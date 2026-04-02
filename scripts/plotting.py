from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

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


def ensure_output_dir(path: Path | str) -> Path:
    output_dir = Path(path)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _format_compact_number(value: float, _pos: int) -> str:
    abs_value = abs(value)
    for threshold, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
        if abs_value >= threshold:
            scaled = value / threshold
            formatted = f"{scaled:.1f}".rstrip("0").rstrip(".")
            return f"{formatted}{suffix}"

    if float(value).is_integer():
        return str(int(value))
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _status_to_color(label: object) -> str:
    return STATUS_COLOR_MAP.get(str(label).strip().lower(), UNKNOWN_STATUS_COLOR)


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
    plt.gca().yaxis.set_major_formatter(FuncFormatter(_format_compact_number))
    plt.title(title)
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
    plt.gca().yaxis.set_major_formatter(FuncFormatter(_format_compact_number))
    plt.title(title)
    plt.ylabel(ylabel)
    plt.xticks(rotation=45, ha="right")
    plt.legend(title="status", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    plt.close()
