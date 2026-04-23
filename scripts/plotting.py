from pathlib import Path
from typing import Any, cast

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import to_rgb
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
# https://www.practicalpythonfordatascience.com/ap_seaborn_palette#tab20b-tab20b-r
VERSION_RANK_COLORS = [
    "#393b79",
    "#5254a3",
    "#6b6ecf",
    "#9c9ede",

    "#637939",
    "#8ca252",
    "#b5cf6b",
    "#cedb9c",

    "#8c6d31",
    "#bd9e39",
    "#e7ba52",
    "#e7cb94",

    "#843c39",
    "#ad494a",
    "#d6616b",
    "#e7969c",

    "#7b4173",
    "#a55194",
    "#ce6dbd",
    "#de9ed6",
]
OTHER_VERSION_COLOR = "#c7c7c7"
SEVERITY_BAR_ORDER = ("critical", "high", "medium", "low", "none")
SEVERITY_BAR_COLOR_MAP = {
    "critical": "#E74C3C",
    "high": "#E67E22",
    "medium": "#F1C40F",
    "low": "#2ECC71",
    "none": "#D0D0D0",
}
AXIS_LABEL_FONTSIZE = 16
TICK_LABEL_FONTSIZE = 14

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


def version_mix_legend_handles(versions: list[object]) -> list[Patch]:
    top_versions = [version for version in versions if str(version) != "Other"]
    colors = build_version_rank_colors(top_versions)
    handles = [Patch(facecolor=color, edgecolor="black", label=str(version)) for version, color in
               zip(top_versions, colors)]
    if any(str(version) == "Other" for version in versions):
        handles.append(Patch(facecolor=OTHER_VERSION_COLOR, edgecolor="black", label="Other"))
    return handles


def save_series_bar_plot(
    series: pd.Series,
    ylabel: str,
    out: Path,
    xlabel: str,
    use_status_colors: bool = False,
    bar_colors: list[str] | None = None,
    bar_top_labels: list[str | None] | None = None,
    legend_handles: list[Any] | None = None,
    legend_title: str | None = None,
):
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
    ax.set_ylabel(ylabel, fontsize=AXIS_LABEL_FONTSIZE)
    ax.set_xlabel(xlabel, fontsize=AXIS_LABEL_FONTSIZE)
    plt.xticks(rotation=45, ha="right", fontsize=TICK_LABEL_FONTSIZE)
    ax.tick_params(axis="y", labelsize=TICK_LABEL_FONTSIZE)
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
    legend_handles: list[Patch],
    annotation_threshold: float = 4.0,
    total_label_padding_pct: float = 12.0,
    total_label_fontsize: float = 8,
    total_label_color: str = "#666666",
):
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
    # Annotate values
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

    # Annotate totals to the right of the bars
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
    ax.set_xlabel(xlabel, fontsize=AXIS_LABEL_FONTSIZE)
    ax.set_ylabel("", fontsize=AXIS_LABEL_FONTSIZE)
    ax.set_xlim(0, 100.0 + total_label_padding_pct)
    plt.yticks(rotation=0, fontsize=TICK_LABEL_FONTSIZE)
    ax.tick_params(axis="x", labelsize=TICK_LABEL_FONTSIZE)
    ax.legend(
        handles=legend_handles,
        title=legend_title,
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        fontsize=8,
        title_fontsize=9,
    )
    plt.tight_layout()
    plt.savefig(out, dpi=150, bbox_inches="tight", pad_inches=0.1)
    plt.close()


def severity_mix_legend_handles() -> list[Patch]:
    return [
        Patch(facecolor=SEVERITY_BAR_COLOR_MAP[severity], edgecolor="black", label=severity)
        for severity in SEVERITY_BAR_ORDER
    ]


def _text_color_for_bar(color: str) -> str:
    red, green, blue = to_rgb(color)
    luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    return "black" if luminance > 0.6 else "white"


def _draw_horizontal_100_row(
    ax: Any,
    y: float,
    row: pd.Series,
    columns: list[object],
    colors: list[str],
    bar_height: float,
    annotate_values: bool = True,
    annotation_threshold: float = 4.0,
    annotate_total: bool = True,
    total_label_y_offset: float = 0.0,
    total_label_padding_pct: float = 12.0,
    total_label_fontsize: float = 8,
    total_label_color: str = "#666666",
    reserve_space: bool = False,
):
    total = float(sum(float(row.get(column, 0)) for column in columns))
    if total <= 0:
        if reserve_space:
            ax.barh(
                y,
                0,
                left=0,
                height=bar_height,
                color="white",
                alpha=0.0,
                edgecolor="none",
                linewidth=0.0,
            )
        return

    left = 0.0
    for column, color in zip(columns, colors):
        raw_value = float(row.get(column, 0))
        if raw_value <= 0:
            continue
        width = raw_value / total * 100.0
        patch = ax.barh(
            y,
            width,
            left=left,
            height=bar_height,
            color=color,
            edgecolor="black",
            linewidth=0.4,
        )
        if annotate_values and width >= annotation_threshold:
            rect = patch.patches[0]
            ax.text(
                rect.get_x() + rect.get_width() / 2,
                rect.get_y() + rect.get_height() / 2,
                format_compact_number(raw_value),
                ha="center",
                va="center",
                fontsize=8,
                color=_text_color_for_bar(color),
                clip_on=True,
            )
        left += width

    # Annotate total to the right of the 2 bars
    if annotate_total and total_label_padding_pct > 0:
        ax.text(
            100.0 + total_label_padding_pct * 0.5,
            y + total_label_y_offset,
            format_compact_number(total),
            ha="center",
            va="center",
            fontsize=total_label_fontsize,
            color=total_label_color,
            clip_on=False,
        )


def save_version_mix_by_csp_dual_plot(
    version_table: pd.DataFrame,
    severity_table: pd.DataFrame,
    out: Path,
    version_legend_handles: list[Patch],
    severity_legend_handles: list[Patch],
    xlabel: str,
    version_legend_title: str,
    severity_legend_title: str,
):
    version_table = version_table.copy().fillna(0)
    severity_table = severity_table.copy().fillna(0)
    version_table = version_table.loc[version_table.sum(axis=1) > 0]
    if version_table.empty:
        print("WARNING: skipping empty version/severity mix plot (no version data to visualize)")
        return

    version_table.index = version_table.index.map(str)
    severity_table.index = severity_table.index.map(str)
    all_csps = list(version_table.index)
    severity_table = severity_table.reindex(all_csps, fill_value=0)
    has_severity_bars = bool(severity_table.size) and bool((severity_table.sum(axis=1) > 0).any())

    version_columns = list(version_table.columns)
    severity_columns = list(severity_table.columns)
    version_palette_labels = [column for column in version_columns if str(column) != "Other"]
    version_palette_colors = dict(zip(version_palette_labels, build_version_rank_colors(version_palette_labels)))
    version_colors = [
        OTHER_VERSION_COLOR if str(column) == "Other" else version_palette_colors.get(column, OTHER_VERSION_COLOR) for
        column in version_columns]
    severity_colors = [SEVERITY_BAR_COLOR_MAP[str(column)] for column in severity_columns] if has_severity_bars else []

    bar_height = 5
    inner_gap = 1
    group_gap = 3
    y_positions: list[float] = []
    label_positions: list[float] = []
    labels: list[str] = []
    row_plan: list[tuple[str, str]] = []
    current_y = 0.0
    for csp in all_csps:
        version_y = current_y
        severity_y = current_y + bar_height + inner_gap
        y_positions.extend([version_y, severity_y])
        label_positions.append(version_y + (bar_height + inner_gap) / 2)
        row_plan.extend([(csp, "version"), (csp, "severity")])
        current_y = severity_y + bar_height + group_gap
        labels.append(csp)

    fig_height = max(6.2, len(all_csps) * 0.8)
    plt.figure(figsize=(12, fig_height))
    ax = plt.gca()

    for (csp, kind), y in zip(row_plan, y_positions):
        if kind == "version":
            _draw_horizontal_100_row(
                ax,
                y,
                version_table.loc[csp],
                version_columns,
                version_colors,
                bar_height,
                annotate_total=True,
                total_label_y_offset=(bar_height + inner_gap) / 2,
            )
        else:
            _draw_horizontal_100_row(
                ax,
                y,
                severity_table.loc[csp],
                severity_columns,
                severity_colors,
                bar_height,
                annotate_total=False,
                reserve_space=not has_severity_bars,
            )
    ax.set_yticks(label_positions)
    ax.set_yticklabels(labels)
    ax.tick_params(axis="both", length=0, pad=8, labelsize=TICK_LABEL_FONTSIZE)
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(PercentFormatter(xmax=100))
    ax.set_xlabel(xlabel, fontsize=AXIS_LABEL_FONTSIZE)
    ax.set_ylabel("", fontsize=AXIS_LABEL_FONTSIZE)
    ax.set_xlim(0, 112)
    legend_artists: list[Any] = []

    if version_legend_handles:
        main_legend = ax.legend(
            handles=version_legend_handles,
            title=version_legend_title,
            bbox_to_anchor=(1.02, 1),
            loc="upper left",
            fontsize=8,
            title_fontsize=9,
        )
        ax.add_artist(main_legend)
        legend_artists.append(main_legend)
    if has_severity_bars and severity_legend_handles:
        severity_legend = ax.legend(
            handles=severity_legend_handles,
            title=severity_legend_title,
            bbox_to_anchor=(1.02, 0.02),
            loc="lower left",
            fontsize=8,
            title_fontsize=9,
        )
        legend_artists.append(severity_legend)

    plt.tight_layout()
    plt.savefig(out, dpi=150, bbox_inches="tight", pad_inches=0.1, bbox_extra_artists=legend_artists)
    plt.close()
