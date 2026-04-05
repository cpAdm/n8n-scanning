from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd
from tabulate import SEPARATING_LINE, tabulate

from csp_loader import CspLookup
from plotting import ensure_output_dir, save_series_bar_plot, save_stacked_bar_plot
from service_types import ServiceAnalyserProto as ServiceAnalyser
from zgrab2_parser import iter_jsonl

TOP_VALUE_MAX_WIDTH = 120
COUNT_LABEL_WIDTH = 12


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
            top_values = "\n".join(f"{count:06}x: {value}" for value, count in counter.most_common(top_n))
            table_rows.append((key if not key_printed else "", csp, len(counter), top_values))
            key_printed = True

        total_counter = total_key_counters[key]
        total_top_values = "\n".join(f"{count:06}x: {value}" for value, count in total_counter.most_common(top_n))
        table_rows.append((key if not key_printed else "", "TOTAL", len(total_counter), total_top_values))
        table_rows.append(SEPARATING_LINE)

    print(f"\n[{service.name}] key value distribution:")
    print(
        tabulate(
            table_rows,
            headers=["Key", "CSP", "Unique count", f"Top ({top_n} values"],
            maxcolwidths=[None, None, None, top_value_max_width],
        )
    )


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

    print_stats_table(service, frame)
    print_distribution_table(service, module_key_counters, total_key_counters, top_n=5)
