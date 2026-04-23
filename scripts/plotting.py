from pathlib import Path
from typing import Any, cast

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch
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
VERSION_RANK_COLORS = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
    "#aec7e8",
    "#ffbb78",
    "#98df8a",
    "#ff9896",
    "#c5b0d5",
    "#c49c94",
    "#f7b6d2",
    "#c7c7c7",
    "#dbdb8d",
    "#9edae5",
]
OTHER_VERSION_COLOR = "#c7c7c7"

SCIENTIFIC_NOTATION_THRESHOLD = 1_000_000_000_000_000


def ensure_output_dir(path: Path | str) -> Path:
    output_dir = Path(path)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def format_compact_number(value: float, *_args) -> str:
    """Formats a number in a compact form with suffixes (K, M, B, T) and scientific notation for very large numbers."""
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
    # noinspection PyTypeChecker
    return STATUS_COLOR_MAP.get(str(label).strip().lower(), UNKNOWN_STATUS_COLOR)


def build_version_rank_colors(labels: list[object]) -> list[str]:
    return [VERSION_RANK_COLORS[idx % len(VERSION_RANK_COLORS)] for idx, _label in enumerate(labels)]


def save_series_bar_plot(
    series: pd.Series,
    ylabel: str,
    out: Path,
    xlabel: str | None = None,
    use_status_colors: bool = False,
    bar_colors: list[str] | None = None,
    bar_top_labels: list[str | None] | None = None,
    legend_handles: list[Any] | None = None,
    legend_title: str | None = None,
) -> None:
    series = series.dropna()
    if series.empty:
        print(f"WARNING: skipping empty plot (no data to visualize)")
        return

    plt.figure(figsize=(10, 5))
    if bar_colors is None:
        plot_colors = [_status_to_color(idx) for idx in series.index] if use_status_colors else None
    else:
        plot_colors = bar_colors
    ax = plt.gca()
    series.plot(kind="bar", ax=ax, color=plot_colors)
    if bar_top_labels is not None:
        max_label_y = 0.0
        y_top = float(ax.get_ylim()[1])
        offset = max(y_top * 0.01, 0.15)
        for patch, label in zip(ax.patches, bar_top_labels):
            if not label:
                continue
            patch_rect = cast(Any, patch)
            x = patch_rect.get_x() + patch_rect.get_width() / 2
            y = float(patch_rect.get_height()) + offset
            max_label_y = max(max_label_y, y)
            ax.text(
                x,
                y,
                str(label),
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
                color="black",
            )
        if max_label_y > y_top:
            ax.set_ylim(top=max_label_y + offset)
    ax.yaxis.set_major_formatter(FuncFormatter(format_compact_number))
    ax.set_ylabel(ylabel)
    if xlabel:
        ax.set_xlabel(xlabel)
    plt.xticks(rotation=45, ha="right")
    if legend_handles:
        ax.legend(handles=legend_handles, title=legend_title, bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    plt.close()


def save_horizontal_stacked_100_plot(
    table: pd.DataFrame,
    xlabel: str,
    out: Path,
    top_n: int,
    legend_title: str,
    bar_colors: list[str],
    legend_handles: list[Patch] | None = None,
    bar_hatches: list[str] | None = None,
    annotate_values: bool = True,
    annotation_threshold: float = 4.0,
    annotate_totals: bool = True,
    total_label_padding_pct: float = 12.0,
    total_label_fontsize: float = 8,
    total_label_color: str = "#666666",
    extra_legend_handles: list[Patch] | None = None,
    extra_legend_title: str | None = None,
    legend_loc: str = "upper left",
    legend_bbox_to_anchor: tuple[float, float] | None = (1.02, 1),
    legend_fontsize: float = 8,
    extra_legend_loc: str = "upper left",
    extra_legend_bbox_to_anchor: tuple[float, float] | None = (1.02, 0.45),
    extra_legend_ncol: int = 1,
    extra_legend_fontsize: float = 8,
) -> None:
    plot_table = table.sort_index()
    if top_n is not None and top_n > 0:
        totals = plot_table.sum(axis=1).rename("total").reset_index()
        totals = totals.sort_values(by=["total", totals.columns[0]], ascending=[False, True], kind="mergesort")
        keep = totals.head(top_n).iloc[:, 0]
        plot_table = plot_table.loc[keep]
        plot_table = plot_table.sort_index()

    if plot_table.empty:
        print(f"WARNING: skipping empty 100% stacked plot (no data to visualize)")
        return

    raw_table = plot_table.copy()
    totals = plot_table.sum(axis=1).replace(0, pd.NA)
    plot_table = plot_table.div(totals, axis=0).fillna(0.0) * 100.0

    plt.figure(figsize=(12, 6))
    ax = plt.gca()
    plot_table.plot(kind="barh", stacked=True, ax=ax, color=bar_colors)
    ax.invert_yaxis()
    if bar_hatches is not None:
        for container, hatch in zip(ax.containers, bar_hatches):
            for patch in getattr(container, "patches", []):
                patch.set_hatch(hatch)
                patch.set_edgecolor("black")
                patch.set_linewidth(0.4)
    if annotate_values:
        for container, column in zip(ax.containers, raw_table.columns):
            for patch, raw_value in zip(getattr(container, "patches", []), raw_table[column].tolist()):
                width = float(patch.get_width())
                if width < annotation_threshold or raw_value <= 0:
                    continue
                x = patch.get_x() + width / 2
                y = patch.get_y() + patch.get_height() / 2
                facecolor = patch.get_facecolor()
                luminance = 0.2126 * facecolor[0] + 0.7152 * facecolor[1] + 0.0722 * facecolor[2]
                text_color = "black" if luminance > 0.6 else "white"
                ax.text(
                    x,
                    y,
                    format_compact_number(float(raw_value)),
                    ha="center",
                    va="center",
                    fontsize=8,
                    color=text_color,
                    clip_on=True,
                )
    if annotate_totals:
        totals = raw_table.sum(axis=1)
        for patch, total in zip(getattr(ax.containers[0], "patches", []), totals.tolist()):
            if total <= 0:
                continue
            y = patch.get_y() + patch.get_height() / 2
            ax.text(
                100.0 + total_label_padding_pct * 0.5,
                y,
                format_compact_number(float(total)),
                ha="center",
                va="center",
                fontsize=total_label_fontsize,
                color=total_label_color,
                clip_on=False,
            )
    ax.xaxis.set_major_formatter(PercentFormatter(xmax=100))
    ax.set_xlabel(xlabel)
    ax.set_ylabel("")
    if annotate_totals and total_label_padding_pct > 0:
        ax.set_xlim(0, 100.0 + total_label_padding_pct)
    plt.yticks(rotation=0)
    main_legend = ax.legend(
        handles=legend_handles,
        title=legend_title,
        bbox_to_anchor=legend_bbox_to_anchor,
        loc=legend_loc,
        fontsize=legend_fontsize,
        title_fontsize=legend_fontsize + 1,
    )
    if extra_legend_handles:
        ax.add_artist(main_legend)
        ax.legend(
            handles=extra_legend_handles,
            title=extra_legend_title or "severity",
            bbox_to_anchor=extra_legend_bbox_to_anchor,
            loc=extra_legend_loc,
            ncol=extra_legend_ncol,
            fontsize=extra_legend_fontsize,
            title_fontsize=extra_legend_fontsize + 1,
        )
    plt.tight_layout()
    plt.savefig(out, dpi=150, bbox_inches="tight", pad_inches=0.1)
    plt.close()
