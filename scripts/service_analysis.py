from collections import Counter
from pathlib import Path
from typing import Any, cast

import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from tabulate import SEPARATING_LINE, tabulate

from csp_loader import CspLookup
from hilbert_prefix_plots import save_service_success_hilbert_plot
from plotting import (
    build_version_family_colors,
    ensure_output_dir,
    OTHER_VERSION_COLOR,
    STATUS_COLOR_MAP,
    UNKNOWN_STATUS_COLOR,
    save_horizontal_stacked_100_plot,
    save_series_bar_plot,
)
from service_types import ServiceAnalyserProto as ServiceAnalyser
from vuln_lookup import NvdVulnerabilityLookup, MATCH_TIERS, SEVERITY_LEVELS
from zgrab2_parser import iter_jsonl

VERSION_TOP_N = 20
UNKNOWN_SEVERITY_COLOR = "#7f7f7f"
SEVERITY_COLOR_MAP = {
    "critical": "#d62728",
    "high": "#ff7f0e",
    "medium": "#bcbd22",
    "low": "#2ca02c",
}
SEVERITY_SHORT_LABEL_MAP = {
    "critical": "C",
    "high": "H",
    "medium": "M",
    "low": "L",
}
OTHER_VERSION_SEVERITY_ORDER = ("critical", "high", "medium", "low", "unknown")


def format_top_count_and_value_lines(items: Any) -> tuple[str, str]:
    pairs = list(items)
    counts = "\n".join(f"{int(count):>{12},}" for value, count in pairs)
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
    table_rows.append(("AGGREGATED", total_counts, total_top_values))

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
    top_n: int,
    top_value_max_width: int,
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
            (key if not key_printed else "", "AGGREGATED", format_total_and_unique_count(total_counter), total_counts,
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


def build_version_mix_by_csp_table(
    frame: pd.DataFrame,
    service: ServiceAnalyser,
    vuln_lookup: NvdVulnerabilityLookup,
    version_top_n: int = VERSION_TOP_N,
) -> pd.DataFrame:
    raw_versions = frame["version"]
    version_series = raw_versions[raw_versions.notna()].apply(normalize_counter_value)
    known_versions = version_series[~version_series.str.lower().isin({"none", "nan", ""})]

    if known_versions.empty:
        return pd.DataFrame()

    version_frame = frame.loc[known_versions.index, ["csp", "vuln_result"]].copy()
    version_frame = version_frame[version_frame["csp"].notna()]
    if version_frame.empty:
        return pd.DataFrame()

    version_frame["version"] = known_versions.loc[version_frame.index]
    top_versions = version_frame["version"].value_counts().head(version_top_n).index
    version_frame["version_grouped"] = version_frame["version"].where(version_frame["version"].isin(top_versions), pd.NA)
    other_mask = version_frame["version_grouped"].isna()
    if other_mask.any():
        version_frame.loc[other_mask, "version_grouped"] = version_frame.loc[other_mask, "vuln_result"].map(
            lambda result: _other_version_bucket_for_result(result, service, vuln_lookup)
        )

    plot_table = version_frame.groupby(["csp", "version_grouped"]).size().unstack(fill_value=0)
    ordered_columns = [version for version in top_versions if version in plot_table.columns]
    ordered_columns.extend(
        bucket
        for bucket in (_other_version_bucket_label(severity) for severity in OTHER_VERSION_SEVERITY_ORDER)
        if bucket in plot_table.columns and bucket not in ordered_columns
    )

    return plot_table.reindex(columns=ordered_columns, fill_value=0)


def build_version_counts_by_csp_table(frame: pd.DataFrame, version_top_n: int = VERSION_TOP_N) -> pd.DataFrame:
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
    if "Other" in plot_table.columns and "Other" not in ordered_columns:
        ordered_columns.append("Other")

    return plot_table.reindex(columns=ordered_columns, fill_value=0)


# https://matplotlib.org/stable/gallery/shapes_and_collections/hatch_style_reference.html
SEVERITY_HATCH_MAP = {
    "critical": "xx",
    "high": "///",
    "medium": "\\\\",
    "low": "..",
}


def _severity_from_counts(counts: dict[str, int]) -> str | None:
    for severity in SEVERITY_LEVELS:
        if int(counts.get(severity, 0)) > 0:
            return severity
    return None


def _version_exact_range_cve_ids(result: Any) -> list[str]:
    exact_ids = set(result.cve_ids_by_confidence.get("exact", []))
    range_ids = set(result.cve_ids_by_confidence.get("range", []))
    return sorted(exact_ids | range_ids)


def _top_version_bar_colors(versions: pd.Series) -> list[str]:
    return build_version_family_colors(list(versions))


def _version_severity_labels(
    frame: pd.DataFrame,
    versions: pd.Series,
    service: ServiceAnalyser,
    vuln_lookup: NvdVulnerabilityLookup,
) -> list[str | None]:
    severities: list[str | None] = []
    for version in versions:
        severities.append(_version_highest_severity_for_version(frame, version, service, vuln_lookup))

    return severities


def _version_highest_severity_for_version(
    frame: pd.DataFrame,
    version: object,
    service: ServiceAnalyser,
    vuln_lookup: NvdVulnerabilityLookup,
) -> str | None:
    version_rows = frame[(frame["version"] == version) & frame["vuln_result"].notna()]
    cve_ids: set[str] = set()
    for result in version_rows["vuln_result"]:
        cve_ids.update(_version_exact_range_cve_ids(result))

    if not cve_ids:
        return None

    severity_counts = vuln_lookup.severity_counts_for_cves(service, sorted(cve_ids))
    return _severity_from_counts(severity_counts)


def _version_row_severity_label(
    result: Any,
    service: ServiceAnalyser,
    vuln_lookup: NvdVulnerabilityLookup,
) -> str | None:
    if result is None:
        return None

    cve_ids = _version_exact_range_cve_ids(result)
    if not cve_ids:
        return None

    severity_counts = vuln_lookup.severity_counts_for_cves(service, cve_ids)
    return _severity_from_counts(severity_counts)


def _other_version_bucket_label(severity: str | None) -> str:
    return f"Other::{severity or 'unknown'}"


def _other_version_bucket_for_result(
    result: Any,
    service: ServiceAnalyser,
    vuln_lookup: NvdVulnerabilityLookup,
) -> str:
    return _other_version_bucket_label(_version_row_severity_label(result, service, vuln_lookup))


def _is_other_version_bucket(column: object) -> bool:
    return str(column).startswith("Other::")


def _other_bucket_severity(column: object) -> str | None:
    text = str(column)
    if not text.startswith("Other::"):
        return None
    return text.split("::", 1)[1]


def _version_bar_hatches(severities: list[str | None]) -> list[str]:
    return [SEVERITY_HATCH_MAP.get(severity, "") for severity in severities]


def _top_version_severity_markers(severities: list[str | None]) -> list[str | None]:
    return [SEVERITY_SHORT_LABEL_MAP.get(severity) for severity in severities]


def _top_version_severity_legend_handles() -> list[Line2D]:
    return [
        Line2D(
            [0],
            [0],
            linestyle="None",
            marker=f"$\\mathregular{{{SEVERITY_SHORT_LABEL_MAP[severity]}}}$",
            markersize=9,
            color="black",
            markeredgewidth=0.0,
            label=severity,
        )
        for severity in ("critical", "high", "medium", "low")
    ]


def _version_severity_legend_handles() -> list[Patch]:
    return [
        Patch(facecolor="white", edgecolor="black", hatch=SEVERITY_HATCH_MAP[severity], label=severity)
        for severity in SEVERITY_LEVELS
    ]


def _version_color_legend_handles(versions: list[object]) -> list[Patch]:
    colors = build_version_family_colors(versions)
    return [Patch(facecolor=color, edgecolor="black", label=str(version)) for version, color in zip(versions, colors)]


def _version_mix_version_legend_handles(columns: list[object]) -> list[Patch]:
    top_versions = [column for column in columns if not _is_other_version_bucket(column)]
    handles = _version_color_legend_handles(top_versions)
    if any(_is_other_version_bucket(column) for column in columns):
        handles.append(Patch(facecolor=OTHER_VERSION_COLOR, edgecolor="black", label="Other"))
    return handles


def _version_mix_bar_colors(columns: list[object]) -> list[str]:
    top_versions = [column for column in columns if not _is_other_version_bucket(column)]
    top_version_colors = dict(zip(top_versions, build_version_family_colors(top_versions)))
    colors: list[str] = []
    for column in columns:
        if _is_other_version_bucket(column):
            colors.append(OTHER_VERSION_COLOR)
        else:
            colors.append(top_version_colors[column])
    return colors


def _version_mix_bar_hatches(
    frame: pd.DataFrame,
    columns: list[object],
    service: ServiceAnalyser,
    vuln_lookup: NvdVulnerabilityLookup,
) -> list[str]:
    hatches: list[str] = []
    for column in columns:
        if _is_other_version_bucket(column):
            hatches.append(SEVERITY_HATCH_MAP.get(_other_bucket_severity(column), ""))
            continue

        severity = _version_highest_severity_for_version(frame, column, service, vuln_lookup)
        hatches.append(SEVERITY_HATCH_MAP.get(severity, ""))
    return hatches


def _status_legend_handles(statuses: list[object]) -> list[Patch]:
    return [
        Patch(facecolor=_status_color(status), edgecolor="black", label=str(status))
        for status in statuses
    ]


def _status_color(status: object) -> str:
    status_key = str(status).strip().lower()
    if status_key in STATUS_COLOR_MAP:
        return STATUS_COLOR_MAP[cast(Any, status_key)]
    return UNKNOWN_STATUS_COLOR


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
    enriched["vuln_critical"] = enriched["vuln_severity_counts"].map(lambda counts: int(counts.get("critical", 0)))
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
                max_critical=("vuln_critical", "max"),
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
                headers=["version", "ips", "CVEs", "critical", "high", "medium", "low", "sample CVEs"],
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

    externally_exploitable["vuln_severity_counts"] = externally_exploitable["vuln_net_no_priv_ids"].map(
        lambda cve_ids: vuln_lookup.severity_counts_for_cves(service, cve_ids)
    )
    externally_exploitable["vuln_critical"] = externally_exploitable["vuln_severity_counts"].map(
        lambda counts: int(counts.get("critical", 0))
    )
    externally_exploitable["vuln_high"] = externally_exploitable["vuln_severity_counts"].map(
        lambda counts: int(counts.get("high", 0))
    )
    externally_exploitable["vuln_medium"] = externally_exploitable["vuln_severity_counts"].map(
        lambda counts: int(counts.get("medium", 0))
    )
    externally_exploitable["vuln_low"] = externally_exploitable["vuln_severity_counts"].map(
        lambda counts: int(counts.get("low", 0))
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
    status_by_csp_table = status_by_csp.pivot(index="csp", columns="status", values="count").fillna(0)
    save_horizontal_stacked_100_plot(
        status_by_csp_table,
        xlabel="Share of IPs",
        out=output_dir / f"{analysis_prefix}_status_by_csp.png",
        top_n=25,
        legend_title="Status",
        bar_colors=[_status_color(status) for status in status_by_csp_table.columns],
        legend_handles=_status_legend_handles(list(status_by_csp_table.columns)),
    )

    overall_status = frame["status"].value_counts()
    save_series_bar_plot(
        overall_status,
        ylabel="IPs",
        out=output_dir / f"{analysis_prefix}_overall_status.png",
        use_status_colors=True,
        legend_handles=_status_legend_handles(list(overall_status.index)),
        legend_title="Status",
    )

    top_versions = frame["version"].dropna().value_counts().head(20)
    top_version_severities = _version_severity_labels(frame, top_versions.index, service, vuln_lookup)
    save_series_bar_plot(
        top_versions,
        ylabel="IPs",
        xlabel="Version",
        out=output_dir / f"{analysis_prefix}_top_versions.png",
        bar_colors=_top_version_bar_colors(top_versions.index),
        bar_top_labels=_top_version_severity_markers(top_version_severities),
        legend_handles=_top_version_severity_legend_handles(),
        legend_title="severity",
    )

    version_mix_by_csp = build_version_mix_by_csp_table(frame, service=service, vuln_lookup=vuln_lookup, version_top_n=VERSION_TOP_N)
    version_mix_columns = list(version_mix_by_csp.columns)
    save_horizontal_stacked_100_plot(
        version_mix_by_csp,
        xlabel="Share of IPs",
        out=output_dir / f"{analysis_prefix}_version_mix_by_csp_100pct.png",
        top_n=VERSION_TOP_N,
        legend_title="version",
        bar_colors=_version_mix_bar_colors(version_mix_columns),
        legend_handles=_version_mix_version_legend_handles(version_mix_columns),
        legend_fontsize=7,
        bar_hatches=_version_mix_bar_hatches(frame, version_mix_columns, service, vuln_lookup),
        extra_legend_handles=_version_severity_legend_handles(),
        extra_legend_title="severity",
        extra_legend_loc="lower left",
        extra_legend_bbox_to_anchor=(1.02, 0.02),
        extra_legend_fontsize=8,
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
    print_distribution_table(service, module_key_counters, total_key_counters, 5, 120)
