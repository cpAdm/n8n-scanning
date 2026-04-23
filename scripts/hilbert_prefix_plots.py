from ipaddress import IPv4Address, IPv4Network
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

DEFAULT_HILBERT_ORDER = 10
DEFAULT_HILBERT_DPI = 180


def _hilbert_rot(n: int, x: int, y: int, rx: int, ry: int) -> tuple[int, int]:
    if ry == 0:
        if rx == 1:
            x = n - 1 - x
            y = n - 1 - y
        x, y = y, x
    return x, y


def _hilbert_d2xy(order: int, distance: int) -> tuple[int, int]:
    side = 1 << order
    x = 0
    y = 0
    t = distance
    s = 1

    while s < side:
        rx = (t // 2) & 1
        ry = (t ^ rx) & 1
        x, y = _hilbert_rot(s, x, y, rx, ry)
        x += s * rx
        y += s * ry
        t //= 4
        s *= 2

    return x, y


def build_csp_hilbert_grid(networks_by_csp: dict[str, list[IPv4Network]], order: int) -> tuple[np.ndarray, list[str]]:
    side = 1 << order
    max_distance = side * side
    bucket_size = 1 << (32 - (2 * order))
    csp_names = sorted(networks_by_csp)

    # -1 means empty; non-negative values map directly to a CSP index in csp_names.
    distance_owner = np.full(max_distance, fill_value=-1, dtype=np.int32)
    for csp_idx, csp in enumerate(csp_names):
        for network in networks_by_csp[csp]:
            start = int(network.network_address)
            end = int(network.broadcast_address)

            start_bucket = max(0, min(start // bucket_size, max_distance - 1))
            end_bucket = max(0, min(end // bucket_size, max_distance - 1))

            for distance in range(start_bucket, end_bucket + 1):
                existing = distance_owner[distance]
                if existing >= 0 and existing != csp_idx:
                    raise ValueError(
                        f"Bucket ownership conflict for distance={distance}: "
                        f"{csp_names[existing]} vs {csp}"
                    )
                distance_owner[distance] = csp_idx

    grid = np.full((side, side), fill_value=-1, dtype=np.int32)
    for distance in np.where(distance_owner >= 0)[0]:
        x, y = _hilbert_d2xy(order, int(distance))
        grid[y, x] = distance_owner[distance]

    return grid, csp_names


def _build_csp_colormap(count: int) -> ListedColormap:
    base = plt.get_cmap("tab20", count) if count <= 20 else plt.get_cmap("gist_ncar", count)
    return ListedColormap([base(i) for i in range(count)], name="csp_colors")


def _build_success_grid(success_ips_by_csp: dict[str, list[str]], csp_names: list[str], order: int) -> np.ndarray:
    side = 1 << order
    max_distance = side * side
    bucket_size = 1 << (32 - (2 * order))

    csp_index = {csp: idx for idx, csp in enumerate(csp_names)}
    distance_owner = np.full(max_distance, fill_value=-1, dtype=np.int32)
    for csp, ips in success_ips_by_csp.items():
        csp_idx = csp_index.get(csp)
        if csp_idx is None:
            continue

        for ip in ips:
            ip_distance = int(IPv4Address(ip)) // bucket_size
            distance = min(max(ip_distance, 0), max_distance - 1)
            existing = distance_owner[distance]
            if existing >= 0 and existing != csp_idx:
                raise ValueError(
                    f"Bucket ownership conflict for distance={distance}: "
                    f"{csp_names[existing]} vs {csp}"
                )
            distance_owner[distance] = csp_idx

    grid = np.full((side, side), fill_value=-1, dtype=np.int32)
    for distance in np.where(distance_owner >= 0)[0]:
        x, y = _hilbert_d2xy(order, int(distance))
        grid[y, x] = distance_owner[distance]

    return grid


def save_service_success_hilbert_plot(
    success_ips_by_csp: dict[str, list[str]],
    all_csp_names: list[str],
    service_name: str,
    out: Path,
    order: int = DEFAULT_HILBERT_ORDER,
    dpi: int = DEFAULT_HILBERT_DPI,
) -> None:
    if not success_ips_by_csp:
        print(f"WARNING: skipping empty plot for '{service_name}' success Hilbert map (no successful IPs)")
        return

    csp_names = sorted(all_csp_names)
    grid = _build_success_grid(success_ips_by_csp, csp_names, order)
    masked_grid = np.ma.masked_where(grid < 0, grid)
    cmap = _build_csp_colormap(len(csp_names))
    csp_to_idx = {csp: idx for idx, csp in enumerate(csp_names)}

    fig, ax = plt.subplots(figsize=(10, 10))
    ax.imshow(masked_grid, origin="lower", interpolation="nearest", cmap=cmap, vmin=0, vmax=max(0, len(csp_names) - 1))
    ax.set_xticks([])
    ax.set_yticks([])

    active_csps = [csp for csp in csp_names if csp in success_ips_by_csp]
    legend_columns = 1 if len(active_csps) <= 14 else 2 if len(active_csps) <= 30 else 3
    ax.legend(
        handles=[Patch(facecolor=cmap(csp_to_idx[csp]), edgecolor="none", label=csp) for csp in active_csps],
        title="CSP",
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        ncol=legend_columns,
        fontsize=8,
        title_fontsize=9,
        frameon=False,
    )

    fig.tight_layout(pad=0.2)
    fig.savefig(out, dpi=dpi, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


def save_combined_hilbert_prefix_plot(
    networks_by_csp: dict[str, list[IPv4Network]],
    out: Path,
    order: int = DEFAULT_HILBERT_ORDER,
    dpi: int = DEFAULT_HILBERT_DPI,
) -> None:
    grid, csp_names = build_csp_hilbert_grid(networks_by_csp, order)
    masked_grid = np.ma.masked_where(grid < 0, grid)
    cmap = _build_csp_colormap(len(csp_names))

    fig, ax = plt.subplots(figsize=(13, 9))
    ax.imshow(masked_grid, origin="lower", interpolation="nearest", cmap=cmap, vmin=0, vmax=max(0, len(csp_names) - 1))
    ax.set_xticks([])
    ax.set_yticks([])

    legend_patches = [Patch(facecolor=cmap(i), edgecolor="none", label=name) for i, name in enumerate(csp_names)]
    legend_columns = 1 if len(csp_names) <= 14 else 2 if len(csp_names) <= 30 else 3
    ax.legend(
        handles=legend_patches,
        title="CSP",
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        ncol=legend_columns,
        fontsize=8,
        title_fontsize=9,
        frameon=False,
    )

    fig.tight_layout()
    fig.savefig(out, dpi=dpi)
    plt.close(fig)
