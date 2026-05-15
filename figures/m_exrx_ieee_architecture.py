from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle


OUT = Path(__file__).resolve().parent
BASE = OUT / "m_exrx_ieee_architecture"


mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 7.0,
        "axes.linewidth": 0.6,
        "figure.dpi": 180,
    }
)


INK = "#111827"
GRAY = "#4b5563"
LIGHT = "#f3f4f6"
VERY_LIGHT = "#f9fafb"
MID = "#9ca3af"
BLUE = "#1f77b4"
BLUE_LIGHT = "#f4f9fd"
RED = "#c0392b"
RED_LIGHT = "#fff7f5"


def add_box(
    ax,
    x,
    y,
    w,
    h,
    title,
    subtitle=None,
    edge=INK,
    face="white",
    lw=0.8,
    title_fs=7.0,
    subtitle_fs=5.8,
):
    patch = Rectangle((x, y), w, h, linewidth=lw, edgecolor=edge, facecolor=face, zorder=2)
    ax.add_patch(patch)
    ax.text(
        x + w / 2,
        y + h * (0.68 if subtitle and "\n" in title else 0.63 if subtitle else 0.50),
        title,
        ha="center",
        va="center",
        weight="bold",
        color=INK,
        fontsize=title_fs,
        linespacing=0.88,
        zorder=3,
    )
    if subtitle:
        ax.text(
            x + w / 2,
            y + h * (0.22 if "\n" in title else 0.28),
            subtitle,
            ha="center",
            va="center",
            color=GRAY,
            fontsize=subtitle_fs,
            linespacing=0.95,
            zorder=3,
        )
    return patch


def add_arrow(ax, start, end, color=INK, lw=0.8, dashed=False, dotted=False, rad=0.0):
    if dotted:
        linestyle = (0, (1.2, 1.8))
    elif dashed:
        linestyle = (0, (3.2, 2.0))
    else:
        linestyle = "solid"
    patch = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=8.5,
        linewidth=lw,
        color=color,
        linestyle=linestyle,
        connectionstyle=f"arc3,rad={rad}",
        shrinkA=2.0,
        shrinkB=2.0,
        zorder=1,
    )
    ax.add_patch(patch)
    return patch


def add_label(ax, x, y, text, size=7.0, color=GRAY, weight="normal", ha="center"):
    ax.text(x, y, text, ha=ha, va="center", color=color, fontsize=size, weight=weight)


def draw():
    fig = plt.figure(figsize=(6.65, 3.25))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    add_label(ax, 0.055, 0.925, "Execution layer", size=7.5, color=INK, weight="bold", ha="left")
    add_label(
        ax,
        0.055,
        0.415,
        "Rule-governed control plane",
        size=7.5,
        color=INK,
        weight="bold",
        ha="left",
    )

    top_y = 0.670
    top_h = 0.135
    cols = [
        (0.055, 0.118, "User\nrequest", "goal + context", INK, "white"),
        (0.215, 0.118, "RiskGate", "R0--R3 triage", RED, RED_LIGHT),
        (0.375, 0.118, "Evidence\nGate", "eligible sources", BLUE, BLUE_LIGHT),
        (0.535, 0.118, "Planner\n+ roles", "draft only", INK, "white"),
        (0.695, 0.118, "Rule\nAuditor", "conflict check", INK, VERY_LIGHT),
        (0.855, 0.100, "Plan\n+ trace", "allowed output", INK, "white"),
    ]

    for x, w, title, subtitle, edge, face in cols:
        add_box(ax, x, top_y, w, top_h, title, subtitle, edge=edge, face=face, lw=0.9)

    for idx in range(len(cols) - 1):
        x, w = cols[idx][0], cols[idx][1]
        nx = cols[idx + 1][0]
        add_arrow(ax, (x + w, top_y + top_h / 2), (nx, top_y + top_h / 2), color=INK, lw=0.8)

    # Unsafe or underspecified requests leave the prescription path early.
    risk_x = cols[1][0] + cols[1][1] / 2
    add_arrow(ax, (risk_x, top_y), (risk_x, 0.580), color=RED, lw=0.8)
    add_box(
        ax,
        0.198,
        0.500,
        0.152,
        0.076,
        "Refuse / ask\n/ refer",
        None,
        edge=RED,
        face="white",
        lw=0.75,
        title_fs=6.4,
    )

    # A single repair loop makes the governance path visible without clutter.
    audit_x = cols[4][0] + cols[4][1] / 2
    plan_x = cols[3][0] + cols[3][1] / 2
    add_arrow(ax, (audit_x, top_y + top_h), (plan_x, top_y + top_h), color=INK, lw=0.75, dashed=True, rad=0.30)
    ax.text(
        0.615,
        0.888,
        "bounded repair / re-audit",
        ha="center",
        va="center",
        color=GRAY,
        fontsize=5.9,
        bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.0},
        zorder=4,
    )

    ax.plot([0.055, 0.955], [0.455, 0.455], color="#d1d5db", linewidth=0.6)

    ctrl_y = 0.165
    ctrl_h = 0.155
    ctrl_cols = [
        (0.055, 0.118, "Profile\nsummary", "versioned", MID, LIGHT, 0.114),
        (0.215, 0.118, "Risk\nrules", "red flags", RED, RED_LIGHT, risk_x),
        (0.375, 0.118, "Evidence\nledger", "id/tier/source", BLUE, BLUE_LIGHT, cols[2][0] + cols[2][1] / 2),
        (0.535, 0.118, "Protocol +\nactions", "HMP library", MID, LIGHT, cols[3][0] + cols[3][1] / 2),
        (0.695, 0.118, "Priority\nladder", "risk > evidence", MID, LIGHT, audit_x),
        (0.855, 0.100, "Audit\nrecord", "repair log", MID, LIGHT, cols[5][0] + cols[5][1] / 2),
    ]

    for x, w, title, subtitle, edge, face, target_x in ctrl_cols:
        add_box(ax, x, ctrl_y, w, ctrl_h, title, subtitle, edge=edge, face=face, lw=0.75)
        add_arrow(
            ax,
            (x + w / 2, ctrl_y + ctrl_h),
            (target_x, top_y),
            color=edge if edge in (BLUE, RED) else GRAY,
            lw=0.65,
            dotted=True,
        )

    add_box(
        ax,
        0.405,
        0.490,
        0.225,
        0.088,
        "Prescription\nContract",
        "status, dose, citations",
        edge=INK,
        face="white",
        lw=0.75,
        title_fs=6.4,
        subtitle_fs=5.4,
    )
    add_arrow(ax, (0.518, 0.578), (0.518, top_y), color=GRAY, lw=0.65, dotted=True)

    add_label(ax, 0.090, 0.060, "solid: execution", size=5.8, color=INK, ha="left")
    add_arrow(ax, (0.195, 0.060), (0.240, 0.060), color=INK, lw=0.75)
    add_label(ax, 0.320, 0.060, "dashed: repair loop", size=5.8, color=INK, ha="left")
    add_arrow(ax, (0.445, 0.060), (0.490, 0.060), color=INK, lw=0.75, dashed=True)
    add_label(ax, 0.570, 0.060, "dotted: governed input", size=5.8, color=INK, ha="left")
    add_arrow(ax, (0.710, 0.060), (0.755, 0.060), color=BLUE, lw=0.75, dotted=True)

    fig.savefig(BASE.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(BASE.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(BASE.with_suffix(".png"), dpi=300, bbox_inches="tight")


if __name__ == "__main__":
    draw()
