from pathlib import Path
import re
from itertools import cycle

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import to_hex
from matplotlib.ticker import FuncFormatter, PercentFormatter

from zgrab2_parser import StatusValue

STATUS_COLOR_MAP: dict[StatusValue, str] = {
    "success": "#2ca02c",
    "connection-refused": "#d62728",
    "connection-timeout": "#ff7f0e",
    "connection-closed": "#ff9896",
    "io-timeout": "#ffbb78",
    "protocol-error": "#9467bd",
    "application-error": "#8c564b",
    "unknown-error": "#7f7f7f",
}
UNKNOWN_STATUS_COLOR = "#1f77b4"
UNKNOWN_VERSION_COLOR = "#9e9e9e"
OTHER_VERSION_COLOR = "#c7c7c7"
# See: https://matplotlib.org/stable/users/explain/colors/colormaps.html#sequential
VERSION_FAMILY_CMAPS = ["Blues", "Greens", "Purples", "Oranges", "Reds", "Greys", "YlGnBu", "PuRd"]
SCIENTIFIC_NOTATION_THRESHOLD = 1_000_000_000_000_000


def ensure_output_dir(path: Path | str) -> Path:
    output_dir = Path(path)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def format_compact_number(value: float, *_args) -> str:
    abs_value = abs(value)
    if abs_value >= SCIENTIFIC_NOTATION_THRESHOLD:
        return f"{value:.3e}"

    suffixes = ("", "K", "M", "B", "T")
    if abs_value >= 1_000:
        magnitude = 0
        scaled_abs = float(abs_value)
        while scaled_abs >= 1000 and magnitude < len(suffixes) - 1:
            scaled_abs /= 1000
            magnitude += 1

        scaled = value / (1000 ** magnitude)
        formatted = f"{scaled:.1f}".rstrip("0").rstrip(".")
        return f"{formatted}{suffixes[magnitude]}"

    if float(value).is_integer():
        return str(int(value))
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _status_to_color(label: object) -> str:
    return STATUS_COLOR_MAP.get(str(label).strip().lower(), UNKNOWN_STATUS_COLOR)


def _extract_major_version_family(label: object) -> str:
    text = str(label).strip()
    if text.lower() == "other":
        return "other"

    match = re.match(r"^(\d+)", text)
    return match.group(1) if match else "unknown"


def _version_family_sort_key(family: str) -> tuple[int, int | str]:
    if family == "other":
        return 2, "other"
    if family == "unknown":
        return 1, "unknown"
    return 0, int(family)


def _build_version_family_colors(labels: list[object]) -> list[str]:
    indices_by_family: dict[str, list[int]] = {}
    for idx, label in enumerate(labels):
        family = _extract_major_version_family(label)
        indices_by_family.setdefault(family, []).append(idx)

    colors: list[str] = [UNKNOWN_VERSION_COLOR] * len(labels)
    cmap_cycle = cycle(VERSION_FAMILY_CMAPS)
    for family in sorted(indices_by_family, key=_version_family_sort_key):
        indices = indices_by_family[family]

        if family == "other":
            for idx in indices:
                colors[idx] = OTHER_VERSION_COLOR
            continue

        if family == "unknown":
            for idx in indices:
                colors[idx] = UNKNOWN_VERSION_COLOR
            continue

        cmap_name = next(cmap_cycle)
        cmap = plt.get_cmap(cmap_name)
        steps = max(len(indices) - 1, 1)

        for shade_pos, idx in enumerate(indices):
            shade = 0.45 + 0.45 * (shade_pos / steps)
            colors[idx] = to_hex(cmap(shade))

    return colors


def save_series_bar_plot(
    series: pd.Series,
    title: str,
    ylabel: str,
    out: Path,
    use_status_colors: bool = False,
) -> None:
    series = series.dropna()
    if series.empty:
        print(f"WARNING: skipping empty plot '{title}' (no data to visualize)")
        return

    plt.figure(figsize=(10, 5))
    bar_colors = [_status_to_color(idx) for idx in series.index] if use_status_colors else None
    series.plot(kind="bar", color=bar_colors)
    plt.gca().yaxis.set_major_formatter(FuncFormatter(format_compact_number))
    # plt.title(title)
    plt.ylabel(ylabel)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    plt.close()


def save_stacked_bar_plot(
    table: pd.DataFrame,
    title: str,
    ylabel: str,
    out: Path,
    top_n: int | None = None,
) -> None:
    plot_table = table.sort_index()
    if top_n is not None and top_n > 0:
        totals = plot_table.sum(axis=1).sort_values(ascending=False)
        keep = totals.head(top_n).index
        plot_table = plot_table.loc[keep]

    if plot_table.empty:
        print(f"WARNING: skipping empty stacked plot '{title}' (no data to visualize)")
        return

    plt.figure(figsize=(12, 6))
    status_colors = [_status_to_color(col) for col in plot_table.columns]
    plot_table.plot(kind="bar", stacked=True, ax=plt.gca(), color=status_colors)
    plt.gca().yaxis.set_major_formatter(FuncFormatter(format_compact_number))
    # plt.title(title)
    plt.ylabel(ylabel)
    plt.xticks(rotation=45, ha="right")
    plt.legend(title="status", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    plt.close()


def save_horizontal_stacked_100_plot(
    table: pd.DataFrame,
    title: str,
    xlabel: str,
    out: Path,
    top_n: int | None = None,
    legend_title: str = "version",
) -> None:
    plot_table = table.sort_index()
    if top_n is not None and top_n > 0:
        totals = plot_table.sum(axis=1).sort_values(ascending=False)
        keep = totals.head(top_n).index
        plot_table = plot_table.loc[keep]

    if plot_table.empty:
        print(f"WARNING: skipping empty 100% stacked plot '{title}' (no data to visualize)")
        return

    totals = plot_table.sum(axis=1).replace(0, pd.NA)
    plot_table = plot_table.div(totals, axis=0).fillna(0.0) * 100.0

    plt.figure(figsize=(12, 6))
    version_colors = _build_version_family_colors(list(plot_table.columns))
    plot_table.plot(kind="barh", stacked=True, ax=plt.gca(), color=version_colors)
    plt.gca().xaxis.set_major_formatter(PercentFormatter(xmax=100))
    # plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel("")
    plt.yticks(rotation=0)
    plt.legend(title=legend_title, bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    plt.close()


