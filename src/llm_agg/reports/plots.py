import math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from textwrap import wrap


def _nice_max(x: float) -> float:
    if x <= 5.5:
        return 5.0
    if x <= 10.5:
        return 10.0
    if x <= 100.5:
        return 100.0
    mag = 10 ** math.floor(math.log10(x))
    return math.ceil(x / mag) * mag

def _two_lines(s: str, width: int) -> str:
    parts = wrap(s, width=width, break_long_words=False)
    if len(parts) <= 1:
        return s
    return parts[0] + "\n" + " ".join(parts[1:])

def plot_180_radar(
    pairs_self: dict[str, float],
    save_to: str,
    title: str | None = "Оценка 180°",
    value_range: tuple[float, float] | None = None,
    show_values: bool = True,
    dpi: int = 200,
    wrap_width: int = 18,
    top_area: float = 0.88,
    title_y: float = 0.985,
    label_radius: float = 1.12,
    value_offset_pts: int = 12
):
    print(f'dict{pairs_self}')
    labels = list(pairs_self.keys())
    values = np.asarray(list(pairs_self.values()), dtype=float)
    print(f'val:{values}')
    fig_bg = "#FBFCFE"
    ax_bg = "#F7F9FC"
    grid_c = "#D6DEE6"
    txt_c = "#2D3A45"
    edge_c = "#4C84B5"
    fill_c = "#4C84B5"

    if value_range is None:
        vmin, vmax = 0.0, _nice_max(np.nanmax(values))
    else:
        vmin, vmax = value_range
        if vmax <= vmin:
            raise ValueError("value_range max must be greater than min.")
    rng = max(vmax - vmin, 1e-12)
    r = np.clip((values - vmin) / rng, 0, 1)

    N = len(labels)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False)
    angles_closed = np.r_[angles, angles[0]]
    r_closed = np.r_[r, r[0]]

    fig = plt.figure(figsize=(7.8, 7.8), dpi=dpi)
    fig.patch.set_facecolor(fig_bg)
    ax = fig.add_subplot(111, projection="polar")
    ax.set_facecolor(ax_bg)

    fig.subplots_adjust(left=0.10, right=0.90, bottom=0.12, top=top_area)
    if title:
        fig.suptitle(title, y=title_y, color=txt_c, fontsize=16, fontweight="semibold")

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 1.0)

    ax.spines["polar"].set_visible(False)
    ax.yaxis.grid(True, color=grid_c, lw=0.8, alpha=0.85)
    ax.xaxis.grid(False)

    ring_levels = [0.25, 0.5, 0.75, 1.0]
    ring_labels = [f"{(vmin + lvl * rng):.0f}" if rng > 5 else f"{(vmin + lvl * rng):g}" for lvl in ring_levels]
    ax.set_yticks(ring_levels)
    ax.set_yticklabels(ring_labels, color="#8EA0B5", fontsize=9)

    ax.set_xticks([])
    labels2 = [_two_lines(lbl, wrap_width) for lbl in labels]
    for ang, text in zip(angles, labels2):
        ax.text(ang, label_radius, text, color=txt_c, fontsize=11, ha="center", va="center", clip_on=False)

    ax.plot(angles_closed, r_closed, color=edge_c, lw=6, alpha=0.06, solid_capstyle="round")
    ax.plot(angles_closed, r_closed, color=edge_c, lw=2.4, alpha=0.9, solid_capstyle="round")
    ax.fill(angles_closed, r_closed, color=fill_c, alpha=0.12)

    ax.scatter(angles, r, s=34, color=fig_bg, edgecolor=edge_c, linewidth=2, zorder=5, alpha=0.9)

    if show_values:
        for ang, rr, val in zip(angles, r, values):
            ax.annotate(
                f"{val:.0f}" if rng > 5 else f"{val:g}",
                xy=(ang, rr),
                xytext=(0, value_offset_pts),
                textcoords="offset points",
                ha="center",
                va="center",
                fontsize=10,
                color=txt_c,
            )

    fig.canvas.draw()
    fig.savefig(save_to, dpi=dpi, facecolor=fig.get_facecolor(), transparent=False)
    plt.close(fig)


def plot_360_radar(
    pairs_self: dict[str, float],
    pairs_mgr: dict[str, float],
    save_to: str,
    title: str | None = "Оценка 360°",
    value_range: tuple[float, float] | None = None,
    dpi: int = 200,
    wrap_width: int = 18,
    top_area: float = 0.86,
    bottom_area: float = 0.14,
    title_y: float = 0.985,
    label_radius: float = 1.12,
    show_values: bool = False,
    value_offset_mgr: int = 12,
    value_offset_self: int = -16,
):
    print(f'{pairs_self=}, {pairs_mgr=}')
    print(f'{pairs_self.keys()=}, {pairs_mgr.keys()=}')
    labels_s = pairs_self.keys()
    labels_m = pairs_mgr.keys()
    
    if labels_s != labels_m:
        raise ValueError("Both inputs must have the same set of disciplines (labels).")

    labels = list(pairs_mgr.keys())
    values_self = np.asarray([pairs_self[lbl] for lbl in labels], dtype=float)
    values_mgr = np.asarray([pairs_mgr[lbl] for lbl in labels], dtype=float)

    fig_bg = "#FBFCFE"
    ax_bg = "#F7F9FC"
    grid_c = "#D6DEE6"
    txt_c = "#2D3A45"
    mgr_c = "#4C84B5"
    self_c = "#5AA6B0"

    if value_range is None:
        vmax = _nice_max(float(np.nanmax(np.r_[values_self, values_mgr])))
        vmin = 0.0
    else:
        vmin, vmax = value_range
        if vmax <= vmin:
            raise ValueError("value_range max must be greater than min.")
    rng = max(vmax - vmin, 1e-12)

    r_self = np.clip((values_self - vmin) / rng, 0, 1)
    r_mgr = np.clip((values_mgr - vmin) / rng, 0, 1)

    N = len(labels)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False)
    angles_closed = np.r_[angles, angles[0]]
    r_self_closed = np.r_[r_self, r_self[0]]
    r_mgr_closed = np.r_[r_mgr, r_mgr[0]]

    fig = plt.figure(figsize=(7.8, 7.8), dpi=dpi)
    fig.patch.set_facecolor(fig_bg)
    ax = fig.add_subplot(111, projection="polar")
    ax.set_facecolor(ax_bg)

    fig.subplots_adjust(left=0.10, right=0.90, bottom=bottom_area, top=top_area)
    if title:
        fig.suptitle(title, y=title_y, color=txt_c, fontsize=16, fontweight="semibold")

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_ylim(0, 1.0)

    ax.spines["polar"].set_visible(False)
    ax.yaxis.grid(True, color=grid_c, lw=0.8, alpha=0.85)
    ax.xaxis.grid(False)

    ring_levels = [0.25, 0.5, 0.75, 1.0]
    ring_labels = [f"{(vmin + lvl * rng):.0f}" if rng > 5 else f"{(vmin + lvl * rng):g}" for lvl in ring_levels]
    ax.set_yticks(ring_levels)
    ax.set_yticklabels(ring_labels, color="#8EA0B5", fontsize=9)

    ax.set_xticks([])
    labels2 = [_two_lines(lbl, wrap_width) for lbl in labels]
    for ang, text in zip(angles, labels2):
        ax.text(ang, label_radius, text, color=txt_c, fontsize=11, ha="center", va="center", clip_on=False)

    ax.plot(angles_closed, r_mgr_closed, color=mgr_c, lw=6, alpha=0.06, solid_capstyle="round")
    ax.plot(angles_closed, r_mgr_closed, color=mgr_c, lw=2.4, alpha=0.85, solid_capstyle="round")
    ax.fill(angles_closed, r_mgr_closed, color=mgr_c, alpha=0.12)

    ax.plot(angles_closed, r_self_closed, color=self_c, lw=6, alpha=0.06, solid_capstyle="round")
    ax.plot(angles_closed, r_self_closed, color=self_c, lw=2.4, alpha=0.85, solid_capstyle="round")
    ax.fill(angles_closed, r_self_closed, color=self_c, alpha=0.12)

    ax.scatter(angles, r_mgr, s=32, color=fig_bg, edgecolor=mgr_c, linewidth=2, zorder=5, alpha=0.9)
    ax.scatter(angles, r_self, s=32, color=fig_bg, edgecolor=self_c, linewidth=2, zorder=5, alpha=0.9)

    if show_values:
        for ang, rr, val in zip(angles, r_mgr, values_mgr):
            ax.annotate(
                f"{val:.0f}",
                xy=(ang, rr),
                xytext=(0, value_offset_mgr),
                textcoords="offset points",
                ha="center",
                va="center",
                fontsize=10,
                color=txt_c,
            )
        for ang, rr, val in zip(angles, r_self, values_self):
            ax.annotate(
                f"{val:.0f}",
                xy=(ang, rr),
                xytext=(0, value_offset_self),
                textcoords="offset points",
                ha="center",
                va="center",
                fontsize=9,
                color=txt_c,
            )

    handles = [
        Line2D([0], [0], color=mgr_c, lw=2.6, marker="o", markersize=5,
               markerfacecolor=fig_bg, markeredgecolor=mgr_c, alpha=0.9),
        Line2D([0], [0], color=self_c, lw=2.6, marker="o", markersize=5,
               markerfacecolor=fig_bg, markeredgecolor=self_c, alpha=0.9),
    ]
    fig.legend(handles, ["Руководство", "Самооценка"], loc="lower center",
               bbox_to_anchor=(0.5, 0.03), ncol=2, frameon=False)

    fig.canvas.draw()
    fig.savefig(save_to, dpi=dpi, facecolor=fig.get_facecolor(), transparent=False)
    plt.close(fig)
