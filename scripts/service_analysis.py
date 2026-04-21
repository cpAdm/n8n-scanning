from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd
from tabulate import SEPARATING_LINE, tabulate

from csp_loader import CspLookup
from hilbert_prefix_plots import save_service_success_hilbert_plot
from plotting import ensure_output_dir, save_horizontal_stacked_100_plot, save_series_bar_plot, save_stacked_bar_plot
from service_types import ServiceAnalyserProto as ServiceAnalyser
from vuln_lookup import NvdVulnerabilityLookup, MATCH_TIERS
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
    vuln_lookup: NvdVulnerabilityLookup,
) -> tuple[list[dict[str, Any]], dict[tuple[str, str], Counter[str]], dict[str, Counter[str]]]:
    rows: list[dict[str, Any]] = []
    module_key_counters: dict[tuple[str, str], Counter[str]] = {}
    total_key_counters: dict[str, Counter[str]] = {}

    for obj in iter_jsonl(Path(jsonl_input_file)):
        ip = obj["ip"]
        module = obj["data"][service.name]
        result = module.get('result')
        csp = csp_lookup.find_csp(ip)
        version = service.get_version(result or {})
        version_text = version.strip() if version else None
        vuln_result = vuln_lookup.lookup(service, version_text) if version_text else None

        rows.append(
            {
                "ip": ip,
                "csp": csp,
                "status": module.get("status"),
                "has_result": bool(result),
                "version": version_text,
                "vuln_result": vuln_result,
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


def print_vulnerabilities_table(
    service: ServiceAnalyser,
    frame: pd.DataFrame,
    vuln_lookup: NvdVulnerabilityLookup,
    top_n: int,
):
    enriched = frame[frame["vuln_result"].notna()].copy()

    def _tier_cve_ids(result: Any) -> list[str]:
        conf = result.confidence
        if conf in MATCH_TIERS:
            return list(result.cve_ids_by_confidence.get(conf, []))
        return []

    enriched["vuln_confidence"] = enriched["vuln_result"].map(lambda result: result.confidence)
    enriched["vuln_cve_ids"] = enriched["vuln_result"].map(_tier_cve_ids)
    enriched["vuln_cve_count"] = enriched["vuln_cve_ids"].map(len)
    enriched = enriched[enriched["vuln_cve_count"] > 0].copy()
    print(f"\n[{service.name}] potential vulnerabilities by version (top {top_n}):")
    if enriched.empty:
        print("No CVE matches found for known versions.")
        return

    enriched["vuln_top_cves"] = enriched["vuln_cve_ids"].map(lambda cve_ids: ", ".join(cve_ids[:5]))

    enriched["vuln_severity_counts"] = enriched["vuln_cve_ids"].map(
        lambda cve_ids: vuln_lookup.severity_counts_for_cves(service, cve_ids)
    )
    enriched["vuln_high"] = enriched["vuln_severity_counts"].map(lambda counts: int(counts.get("high", 0)))
    enriched["vuln_medium"] = enriched["vuln_severity_counts"].map(lambda counts: int(counts.get("medium", 0)))
    enriched["vuln_low"] = enriched["vuln_severity_counts"].map(lambda counts: int(counts.get("low", 0)))

    for confidence in MATCH_TIERS:
        subset = enriched[enriched["vuln_confidence"] == confidence]
        if subset.empty:
            continue

        summary = (
            subset.groupby(["version"], dropna=False)
            .agg(
                ips=("ip", "count"),
                max_cve_count=("vuln_cve_count", "max"),
                max_high=("vuln_high", "max"),
                max_medium=("vuln_medium", "max"),
                max_low=("vuln_low", "max"),
                sample_cves=("vuln_top_cves", "first"),
            )
            .sort_values(["ips", "max_cve_count"], ascending=False)
            .head(top_n)
            .reset_index()
        )

        print(f"\nConfidence: {confidence} (top {top_n})")
        print(
            tabulate(
                summary,
                headers=["version", "ips", "CVEs", "high", "medium", "low", "sample CVEs"],
                showindex=False,
            )
        )

    externally_exploitable = enriched.copy()
    externally_exploitable["vuln_net_no_priv_ids"] = externally_exploitable["vuln_cve_ids"].map(
        lambda cve_ids: vuln_lookup.network_no_privilege_cve_ids_for_cves(service, cve_ids)
    )
    externally_exploitable["vuln_net_no_priv_count"] = externally_exploitable["vuln_net_no_priv_ids"].map(len)
    externally_exploitable = externally_exploitable[externally_exploitable["vuln_net_no_priv_count"] > 0].copy()

    print(
        f"\n[{service.name}] network-exploitable (no privileges required) vulnerabilities by version (top {top_n}):"
    )
    if externally_exploitable.empty:
        print("No network/no-privilege CVE matches found for known versions.")
        return

    externally_exploitable["vuln_net_no_priv_top_cves"] = externally_exploitable["vuln_net_no_priv_ids"].map(
        lambda cve_ids: ", ".join(cve_ids[:5])
    )

    for confidence in MATCH_TIERS:
        subset = externally_exploitable[externally_exploitable["vuln_confidence"] == confidence]
        if subset.empty:
            continue

        summary = (
            subset.groupby(["version"], dropna=False)
            .agg(
                ips=("ip", "count"),
                max_cve_count=("vuln_net_no_priv_count", "max"),
                sample_cves=("vuln_net_no_priv_top_cves", "first"),
            )
            .sort_values(["ips", "max_cve_count"], ascending=False)
            .head(top_n)
            .reset_index()
        )

        print(f"\nConfidence: {confidence} (top {top_n})")
        print(
            tabulate(
                summary,
                headers=["version", "ips", "CVEs", "sample CVEs"],
                showindex=False,
            )
        )


def analyse_generic_service(
    service: ServiceAnalyser,
    jsonl_input_file: Path,
    csp_lookup: CspLookup,
    output_root: Path,
    vuln_lookup: NvdVulnerabilityLookup,
):
    output_dir = ensure_output_dir(Path(output_root))
    analysis_prefix = f"{Path(jsonl_input_file).stem}_{service.name}_analysis"

    rows, module_key_counters, total_key_counters = collect_service_rows_and_counters(
        jsonl_input_file=jsonl_input_file,
        service=service,
        csp_lookup=csp_lookup,
        vuln_lookup=vuln_lookup,
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
        all_csp_names=sorted(csp_lookup.networks_by_csp_v4),
        service_name=service.display_name,
        out=output_dir / f"{analysis_prefix}_success_hilbert.png",
    )

    print_stats_table(service, frame)
    print_versions_table(service, frame, top_n=5)
    print_vulnerabilities_table(service, frame, vuln_lookup=vuln_lookup, top_n=5)
    print_distribution_table(service, module_key_counters, total_key_counters, top_n=5)
