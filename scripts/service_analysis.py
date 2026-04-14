from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd
from tabulate import SEPARATING_LINE, tabulate

from csp_loader import CspLookup
from hilbert_prefix_plots import save_service_success_hilbert_plot
from plotting import ensure_output_dir, save_horizontal_stacked_100_plot, save_series_bar_plot, save_stacked_bar_plot
from service_types import ServiceAnalyserProto as ServiceAnalyser
from zgrab2_parser import iter_jsonl

TOP_VALUE_MAX_WIDTH = 120
COUNT_LABEL_WIDTH = 12
VERSION_TOP_N = 10
CSP_TOP_N_FOR_VERSION_PLOT = 25


def format_top_count_and_value_lines(items: Any) -> tuple[str, str]:
    pairs = list(items)
    counts = "\n".join(f"{int(count):>{COUNT_LABEL_WIDTH},}" for value, count in pairs)
    values = "\n".join(str(value) for value, count in pairs)
    return counts, values


def format_total_and_unique_count(counter: Counter[str]) -> str:
    total_count = sum(counter.values())
    unique_count = len(counter)
    return f"{total_count:,}\n(unique: {unique_count:,})"


def normalize_counter_value(value: Any) -> str:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return str(value)
    if isinstance(value, (dict, list, tuple, set)):
        return repr(value)
    return repr(value)


def collect_service_rows_and_counters(
    jsonl_input_file: Path | str,
    service: ServiceAnalyser,
    csp_lookup: CspLookup,
) -> tuple[list[dict[str, Any]], dict[tuple[str, str], Counter[str]], dict[str, Counter[str]]]:
    rows: list[dict[str, Any]] = []
    module_key_counters: dict[tuple[str, str], Counter[str]] = {}
    total_key_counters: dict[str, Counter[str]] = {}

    for obj in iter_jsonl(Path(jsonl_input_file)):
        ip = obj["ip"]
        module = obj["data"].get(service.name)
        csp = csp_lookup.find_csp(ip)
        rows.append(
            {
                "ip": ip,
                "csp": csp,
                "status": module.get("status"),
                "has_result": module.get("result") is not None,
                "version": service.get_version(module),
            }
        )

        for key, value in module.items():
            normalized_value = normalize_counter_value(value)
            module_key_counters.setdefault((csp, key), Counter())[normalized_value] += 1
            total_key_counters.setdefault(key, Counter())[normalized_value] += 1

    return rows, module_key_counters, total_key_counters


def print_stats_table(service: ServiceAnalyser, frame: pd.DataFrame):
    print(f"\n[{service.name}] overall stats:")
    stats = {
        "rows": int(len(frame)),
        "unique_ips": int(frame["ip"].nunique()),
        "unique_csps": int(frame["csp"].nunique()),
    }
    print(
        tabulate(
            [
                ("rows", f"{stats['rows']:,}"),
                ("unique_ips", f"{stats['unique_ips']:,}"),
                ("unique_csps", f"{stats['unique_csps']:,}"),
            ],
            headers=["Metric", "Value"],
            intfmt=","
        )
    )


def print_versions_table(service: ServiceAnalyser, frame: pd.DataFrame, top_n: int = 5):
    # Filter out pandas-missing values before string normalization (prevents literal "nan" rows)
    raw_versions = frame["version"]
    version_series = raw_versions[raw_versions.notna()].apply(normalize_counter_value)
    known_versions = version_series[~version_series.str.lower().isin({"none", "nan", ""})]

    print(f"\n[{service.name}] versions (top {top_n} per CSP):")
    if known_versions.empty:
        print("No versions available.")
        return

    table_rows: list[Any] = []
    for csp in sorted(frame["csp"].dropna().unique()):
        csp_raw_versions = frame.loc[frame["csp"] == csp, "version"]
        csp_versions = csp_raw_versions[csp_raw_versions.notna()].apply(normalize_counter_value)
        csp_versions = csp_versions[~csp_versions.str.lower().isin({"none", "nan", ""})]
        if csp_versions.empty:
            continue

        top_counts, top_values = format_top_count_and_value_lines(csp_versions.value_counts().head(top_n).items())
        table_rows.append((csp, top_counts, top_values))

    total_counts, total_top_values = format_top_count_and_value_lines(known_versions.value_counts().head(top_n).items())
    table_rows.append(SEPARATING_LINE)
    table_rows.append(("TOTAL", total_counts, total_top_values))

    print(
        tabulate(
            table_rows,
            headers=["CSP", "Top counts", "Top versions"],
            intfmt=",",
            colalign=("left", "right", "left"),
        )
    )


def print_distribution_table(
    service: ServiceAnalyser,
    module_key_counters: dict[tuple[str, str], Counter[str]],
    total_key_counters: dict[str, Counter[str]],
    top_n: int = 5,
    top_value_max_width: int = TOP_VALUE_MAX_WIDTH,
):
    table_rows: list[Any] = []
    keys = sorted(total_key_counters)

    for key in keys:
        key_printed = False

        for csp in sorted(csp for csp, module_key in module_key_counters if module_key == key):
            counter = module_key_counters[(csp, key)]
            top_counts, top_values = format_top_count_and_value_lines(counter.most_common(top_n))
            table_rows.append(
                (key if not key_printed else "", csp, format_total_and_unique_count(counter), top_counts, top_values))
            key_printed = True

        total_counter = total_key_counters[key]
        total_counts, total_top_values = format_top_count_and_value_lines(total_counter.most_common(top_n))
        table_rows.append(
            (key if not key_printed else "", "TOTAL", format_total_and_unique_count(total_counter), total_counts,
             total_top_values))
        table_rows.append(SEPARATING_LINE)

    print(f"\n[{service.name}] key value distribution:")
    print(
        tabulate(
            table_rows,
            headers=["Key", "CSP", "Count", f"Top {top_n} counts", f"Top {top_n} values"],
            maxcolwidths=[None, None, None, None, top_value_max_width],
            intfmt=",",
            colalign=("left", "left", "right", "right", "left"),
        )
    )


def build_version_mix_by_csp_table(frame: pd.DataFrame, version_top_n: int = VERSION_TOP_N) -> pd.DataFrame:
    raw_versions = frame["version"]
    version_series = raw_versions[raw_versions.notna()].apply(normalize_counter_value)
    known_versions = version_series[~version_series.str.lower().isin({"none", "nan", ""})]

    if known_versions.empty:
        return pd.DataFrame()

    version_frame = frame.loc[known_versions.index, ["csp"]].copy()
    version_frame = version_frame[version_frame["csp"].notna()]
    if version_frame.empty:
        return pd.DataFrame()

    version_frame["version"] = known_versions.loc[version_frame.index]
    top_versions = version_frame["version"].value_counts().head(version_top_n).index
    version_frame["version_grouped"] = version_frame["version"].where(
        version_frame["version"].isin(top_versions),
        "Other",
    )

    plot_table = version_frame.groupby(["csp", "version_grouped"]).size().unstack(fill_value=0)
    ordered_columns = [version for version in top_versions if version in plot_table.columns]
    if "Other" in plot_table.columns:
        ordered_columns.append("Other")

    return plot_table.reindex(columns=ordered_columns, fill_value=0)


def analyse_generic_service(
    service: ServiceAnalyser,
    jsonl_input_file: Path,
    csp_lookup: CspLookup,
    output_root: Path,
):
    output_dir = ensure_output_dir(Path(output_root))
    analysis_prefix = f"{Path(jsonl_input_file).stem}_{service.name}_analysis"

    rows, module_key_counters, total_key_counters = collect_service_rows_and_counters(
        jsonl_input_file=jsonl_input_file,
        service=service,
        csp_lookup=csp_lookup,
    )

    frame = pd.DataFrame(rows)
    if frame.empty:
        print("WARNING: No data available for this service. Skipping analysis.")
        return

    status_by_csp = frame.groupby(["csp", "status"]).size().rename("count").reset_index()
    save_stacked_bar_plot(
        status_by_csp.pivot(index="csp", columns="status", values="count").fillna(0),
        title=f"{service.display_name} status by CSP",
        ylabel="IPs",
        out=output_dir / f"{analysis_prefix}_status_by_csp.png",
        top_n=25,
    )

    save_series_bar_plot(
        frame["status"].value_counts(),
        title=f"{service.display_name} overall status distribution",
        ylabel="IPs",
        out=output_dir / f"{analysis_prefix}_overall_status.png",
        use_status_colors=True,
    )

    save_series_bar_plot(
        frame["version"].dropna().value_counts().head(20),
        title=f"{service.display_name} versions/banners (top 20)",
        ylabel="IPs",
        out=output_dir / f"{analysis_prefix}_top_versions.png",
    )

    version_mix_by_csp = build_version_mix_by_csp_table(frame, version_top_n=VERSION_TOP_N)
    save_horizontal_stacked_100_plot(
        version_mix_by_csp,
        title=f"{service.display_name} version mix by CSP (100% stacked)",
        xlabel="Share of IPs",
        out=output_dir / f"{analysis_prefix}_version_mix_by_csp_100pct.png",
        top_n=CSP_TOP_N_FOR_VERSION_PLOT,
        legend_title="version",
    )

    success_frame = frame.loc[frame["status"] == "success", ["csp", "ip"]].dropna(subset=["csp", "ip"]).copy()
    success_frame["ip"] = success_frame["ip"].astype(str)
    save_service_success_hilbert_plot(
        success_ips_by_csp={
            str(csp): sorted(set(group["ip"]))
            for csp, group in success_frame.groupby("csp", sort=True)
        },
        all_csp_names=sorted(csp_lookup.networks_by_csp),
        service_name=service.display_name,
        out=output_dir / f"{analysis_prefix}_success_hilbert.png",
    )

    print_stats_table(service, frame)
    print_versions_table(service, frame, top_n=5)
    print_distribution_table(service, module_key_counters, total_key_counters, top_n=5)
