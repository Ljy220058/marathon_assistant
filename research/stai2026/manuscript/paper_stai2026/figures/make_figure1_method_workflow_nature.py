"""Generate the publication-style workflow schematic for Figure 1.

Backend: Python/matplotlib only, following the local nature-figure workflow.
The figure is a schematic-led composite: the workflow itself is the evidence.
"""

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


OUT = Path(__file__).resolve().parent

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 7,
    }
)

PALETTE = {
    "ink": "#1F2937",
    "muted": "#64748B",
    "neutral_fill": "#F8FAFC",
    "neutral_edge": "#CBD5E1",
    "evidence_fill": "#EEF4FF",
    "evidence_edge": "#3B6FB6",
    "safety_fill": "#FFF1F2",
    "safety_edge": "#C2413B",
    "generate_fill": "#F0F8F2",
    "generate_edge": "#3F8F57",
    "repair_fill": "#FFF7ED",
    "repair_edge": "#C97817",
    "refusal_fill": "#FFF5F5",
    "refusal_edge": "#B42318",
}


def add_box(ax, xy, wh, title, subtitle="", fill="#FFFFFF", edge="#222222", lw=0.9):
    x, y = xy
    w, h = wh
    box = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.014,rounding_size=0.035",
        facecolor=fill,
        edgecolor=edge,
        linewidth=lw,
    )
    ax.add_patch(box)
    lines = title.split("\n")
    if len(lines) == 1:
        y_positions = [y + h * (0.62 if subtitle else 0.52)]
        subtitle_y = y + h * 0.31
    else:
        y_positions = [y + h * 0.68, y + h * 0.48]
        subtitle_y = y + h * 0.22
    for line, yy in zip(lines, y_positions):
        ax.text(
            x + w / 2,
            yy,
            line,
            ha="center",
            va="center",
            fontsize=5.6,
            fontweight="bold",
            color=PALETTE["ink"],
        )
    if subtitle:
        ax.text(
            x + w / 2,
            subtitle_y,
            subtitle,
            ha="center",
            va="center",
            fontsize=4.4,
            color=PALETTE["muted"],
        )
    return box


def arrow(ax, start, end, color=None, dashed=False, rad=0.0, lw=0.9, ms=8):
    patch = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=ms,
        linewidth=lw,
        color=color or PALETTE["ink"],
        linestyle=(0, (3, 2.4)) if dashed else "solid",
        connectionstyle=f"arc3,rad={rad}",
        shrinkA=2,
        shrinkB=2,
    )
    ax.add_patch(patch)
    return patch


def main():
    # Double-column Nature-style width: 183 mm. Ultra-clean schematic for 8-page LNCS.
    fig, ax = plt.subplots(figsize=(7.2, 2.35), dpi=300)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.patch.set_facecolor("white")

    y = 0.64
    h = 0.18
    w = 0.098
    gap = 0.026
    x0 = 0.012

    boxes = {}
    steps = [
        ("query", "User\nquery", "", PALETTE["neutral_fill"], PALETTE["neutral_edge"]),
        ("pre", "Pre-gate", "filter", PALETTE["safety_fill"], PALETTE["safety_edge"]),
        ("ret", "Retrieve", "evidence", PALETTE["evidence_fill"], PALETTE["evidence_edge"]),
        ("eg", "Evidence\ngate", "sufficiency", PALETTE["evidence_fill"], PALETTE["evidence_edge"]),
        ("rg", "Risk\ngate", "safety", PALETTE["safety_fill"], PALETTE["safety_edge"]),
        ("gen", "Generator", "constrained", PALETTE["generate_fill"], PALETTE["generate_edge"]),
        ("aud", "Auditor", "grounding", PALETTE["generate_fill"], PALETTE["generate_edge"]),
        ("final", "Final\nanswer", "verified", PALETTE["neutral_fill"], PALETTE["neutral_edge"]),
    ]

    for i, (key, title, subtitle, fill, edge) in enumerate(steps):
        x = x0 + i * (w + gap)
        boxes[key] = (x, y, w, h)
        add_box(ax, (x, y), (w, h), title, subtitle, fill, edge)

    for i in range(len(steps) - 1):
        k1 = steps[i][0]
        k2 = steps[i + 1][0]
        x1, y1, w1, h1 = boxes[k1]
        x2, y2, _, h2 = boxes[k2]
        arrow(ax, (x1 + w1 + 0.004, y1 + h1 / 2), (x2 - 0.004, y2 + h2 / 2), lw=0.85, ms=7)

    # Refusal and repair modules.
    ref_xy = (0.35, 0.24)
    ref_wh = (0.19, 0.15)
    add_box(
        ax,
        ref_xy,
        ref_wh,
        "Refusal",
        "no answer",
        PALETTE["refusal_fill"],
        PALETTE["refusal_edge"],
        lw=1.0,
    )

    rep_xy = (0.705, 0.24)
    rep_wh = (0.19, 0.15)
    add_box(
        ax,
        rep_xy,
        rep_wh,
        "Bounded repair",
        "citation + grounding",
        PALETTE["repair_fill"],
        PALETTE["repair_edge"],
        lw=1.0,
    )

    # Refusal-capable control points.
    refusal_sources = [
        ("pre", (boxes["pre"][0] + boxes["pre"][2] * 0.5, y - 0.004), (ref_xy[0] + 0.03, ref_xy[1] + ref_wh[1] * 0.65), -0.02),
        ("eg", (boxes["eg"][0] + boxes["eg"][2] * 0.5, y - 0.004), (ref_xy[0] + ref_wh[0] * 0.46, ref_xy[1] + ref_wh[1] + 0.003), 0.0),
        ("rg", (boxes["rg"][0] + boxes["rg"][2] * 0.5, y - 0.004), (ref_xy[0] + ref_wh[0] - 0.025, ref_xy[1] + ref_wh[1] * 0.72), 0.02),
        ("aud", (boxes["aud"][0] + boxes["aud"][2] * 0.42, y - 0.004), (ref_xy[0] + ref_wh[0] * 0.98, ref_xy[1] + ref_wh[1] * 0.58), 0.02),
    ]
    for _, start, end, rad in refusal_sources:
        arrow(ax, start, end, color=PALETTE["refusal_edge"], dashed=True, rad=rad, lw=0.85, ms=7)

    ax.text(
        ref_xy[0] + ref_wh[0] / 2,
        ref_xy[1] - 0.045,
        "Only four modules can trigger refusal",
        ha="center",
        va="top",
        fontsize=4.6,
        color=PALETTE["refusal_edge"],
        fontweight="bold",
    )

    # Audit/repair loop.
    aud = boxes["aud"]
    arrow(ax, (aud[0] + aud[2] * 0.5, aud[1] - 0.004), (rep_xy[0] + rep_wh[0] * 0.38, rep_xy[1] + ref_wh[1] + 0.003), color=PALETTE["repair_edge"], dashed=True, rad=0.03, lw=0.85, ms=7)
    arrow(ax, (rep_xy[0] + rep_wh[0] * 0.68, rep_xy[1] + rep_wh[1] + 0.003), (aud[0] + aud[2] * 0.82, aud[1] - 0.004), color=PALETTE["repair_edge"], dashed=True, rad=-0.18, lw=0.85, ms=7)
    ax.text(rep_xy[0] + rep_wh[0] / 2, rep_xy[1] + rep_wh[1] + 0.055, "repair then re-audit", ha="center", va="bottom", fontsize=4.6, color=PALETTE["repair_edge"], fontweight="bold")

    ax.text(
        0.5,
        0.075,
        "Vanilla RAG: retrieve → generate → answer.   Proposed workflow: retrieve → gate → generate → audit → repair or refuse.",
        ha="center",
        va="center",
        fontsize=5.0,
        color=PALETTE["muted"],
    )

    base = OUT / "figure1_method_workflow_nature"
    fig.savefig(base.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(base.with_suffix(".png"), dpi=600, bbox_inches="tight")
    fig.savefig(base.with_suffix(".tiff"), dpi=600, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
