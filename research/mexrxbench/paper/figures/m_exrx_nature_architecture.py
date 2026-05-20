from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle


OUT = Path(__file__).resolve().parent
BASE = OUT / "m_exrx_nature_architecture"


mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 7,
        "axes.linewidth": 0.5,
        "figure.dpi": 160,
    }
)


COLORS = {
    "ink": "#1f2937",
    "muted": "#6b7280",
    "line": "#9ca3af",
    "panel": "#f8fafc",
    "risk": "#e76f51",
    "risk_bg": "#fff4ef",
    "evidence": "#457b9d",
    "evidence_bg": "#eef6fb",
    "contract": "#5b5f97",
    "contract_bg": "#f1f2fb",
    "expert": "#2a9d8f",
    "expert_bg": "#eefaf7",
    "audit": "#7b2cbf",
    "audit_bg": "#f6efff",
    "output": "#4b8f29",
    "output_bg": "#f0f8ec",
}


def box(ax, x, y, w, h, title, lines=None, fc="#ffffff", ec=None, lw=0.9, r=0.035):
    ec = ec or COLORS["line"]
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0.012,rounding_size={r}",
        linewidth=lw,
        edgecolor=ec,
        facecolor=fc,
        mutation_aspect=1,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h * 0.62, title, ha="center", va="center", weight="bold", color=COLORS["ink"])
    if lines:
        for idx, line in enumerate(lines):
            ax.text(
                x + w / 2,
                y + h * (0.36 - idx * 0.18),
                line,
                ha="center",
                va="center",
                color=COLORS["muted"],
                fontsize=6.2,
            )
    return patch


def label(ax, x, y, text, color=None, size=6.2, weight="normal", ha="center"):
    ax.text(x, y, text, ha=ha, va="center", color=color or COLORS["muted"], fontsize=size, weight=weight)


def arrow(ax, xy1, xy2, color=None, lw=0.9, rad=0.0, style="-|>", dashed=False):
    patch = FancyArrowPatch(
        xy1,
        xy2,
        arrowstyle=style,
        mutation_scale=8.5,
        linewidth=lw,
        color=color or COLORS["ink"],
        connectionstyle=f"arc3,rad={rad}",
        linestyle=(0, (3, 2)) if dashed else "solid",
        shrinkA=3,
        shrinkB=3,
    )
    ax.add_patch(patch)
    return patch


def capsule(ax, x, y, w, h, text, fc="#ffffff", ec=None, color=None):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.006,rounding_size=0.04",
        linewidth=0.6,
        edgecolor=ec or COLORS["line"],
        facecolor=fc,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=5.8, color=color or COLORS["muted"])


def draw():
    fig = plt.figure(figsize=(7.2, 4.8))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.035, 0.955, "Rule-governed M-EXRx agent", fontsize=10.5, weight="bold", color=COLORS["ink"])
    ax.text(
        0.035,
        0.925,
        "Evidence-gated, risk-aware multi-expert workflow for endurance exercise prescription",
        fontsize=6.8,
        color=COLORS["muted"],
    )

    ax.text(0.035, 0.875, "a", fontsize=9, weight="bold", color=COLORS["ink"])
    ax.text(0.060, 0.875, "Governed prescription pathway", fontsize=7.5, weight="bold", color=COLORS["ink"])

    box(ax, 0.045, 0.700, 0.105, 0.105, "User\nquery", ["goal, profile", "constraints"], fc="#ffffff")
    box(ax, 0.190, 0.685, 0.130, 0.135, "RiskGate", ["R0-R3 risk", "red flags"], fc=COLORS["risk_bg"], ec=COLORS["risk"], lw=1.1)
    box(
        ax,
        0.365,
        0.685,
        0.140,
        0.135,
        "EvidenceGate",
        ["answerable?", "tier policy"],
        fc=COLORS["evidence_bg"],
        ec=COLORS["evidence"],
        lw=1.1,
    )
    box(
        ax,
        0.550,
        0.675,
        0.160,
        0.155,
        "Prescription\ncontract",
        ["FITT-VP, phase", "capacity budget"],
        fc=COLORS["contract_bg"],
        ec=COLORS["contract"],
        lw=1.25,
    )
    box(
        ax,
        0.755,
        0.675,
        0.160,
        0.155,
        "Dynamic\nexpert panel",
        ["default 3 roles", "conditional experts"],
        fc=COLORS["expert_bg"],
        ec=COLORS["expert"],
        lw=1.1,
    )
    box(ax, 0.940, 0.690, 0.050, 0.125, "Plan\n+\ntrace", None, fc=COLORS["output_bg"], ec=COLORS["output"], lw=1.1)

    arrow(ax, (0.150, 0.752), (0.190, 0.752), COLORS["ink"])
    arrow(ax, (0.320, 0.752), (0.365, 0.752), COLORS["risk"])
    arrow(ax, (0.505, 0.752), (0.550, 0.752), COLORS["evidence"])
    arrow(ax, (0.710, 0.752), (0.755, 0.752), COLORS["contract"])
    arrow(ax, (0.915, 0.752), (0.940, 0.752), COLORS["expert"])

    capsule(ax, 0.183, 0.635, 0.145, 0.035, "red flags override goals", fc="#ffffff", ec=COLORS["risk"], color=COLORS["risk"])
    capsule(ax, 0.355, 0.635, 0.158, 0.035, "no evidence, no prescription", fc="#ffffff", ec=COLORS["evidence"], color=COLORS["evidence"])
    capsule(ax, 0.555, 0.635, 0.150, 0.035, "contract before generation", fc="#ffffff", ec=COLORS["contract"], color=COLORS["contract"])

    ax.text(0.035, 0.555, "b", fontsize=9, weight="bold", color=COLORS["ink"])
    ax.text(0.060, 0.555, "Shared evidence and rule substrate", fontsize=7.5, weight="bold", color=COLORS["ink"])

    substrate = FancyBboxPatch(
        (0.045, 0.160),
        0.615,
        0.350,
        boxstyle="round,pad=0.012,rounding_size=0.025",
        linewidth=0.7,
        edgecolor="#d1d5db",
        facecolor=COLORS["panel"],
    )
    ax.add_patch(substrate)

    box(ax, 0.075, 0.395, 0.125, 0.090, "Protocol rules", ["HMP, safety"], fc="#ffffff", lw=0.7)
    box(ax, 0.225, 0.395, 0.125, 0.090, "Action library", ["workout templates"], fc="#ffffff", lw=0.7)
    box(ax, 0.375, 0.395, 0.125, 0.090, "Safety KB", ["pain, referral"], fc="#ffffff", lw=0.7)
    box(ax, 0.525, 0.395, 0.105, 0.090, "Nutrition KB", ["fueling"], fc="#ffffff", lw=0.7)
    box(
        ax,
        0.190,
        0.245,
        0.185,
        0.095,
        "Unified\nEvidenceBundle",
        ["id, tier, source", "snippet, page"],
        fc=COLORS["evidence_bg"],
        ec=COLORS["evidence"],
        lw=1.0,
    )
    box(
        ax,
        0.440,
        0.245,
        0.165,
        0.095,
        "Explanation-only",
        ["literature, wiki", "notes"],
        fc="#ffffff",
        lw=0.7,
    )
    arrow(ax, (0.138, 0.395), (0.250, 0.340), COLORS["evidence"], lw=0.75)
    arrow(ax, (0.288, 0.395), (0.288, 0.340), COLORS["evidence"], lw=0.75)
    arrow(ax, (0.438, 0.395), (0.340, 0.340), COLORS["evidence"], lw=0.75)
    arrow(ax, (0.578, 0.395), (0.522, 0.340), COLORS["line"], lw=0.75)

    ax.text(0.690, 0.555, "c", fontsize=9, weight="bold", color=COLORS["ink"])
    ax.text(0.715, 0.555, "Audit and arbitration", fontsize=7.5, weight="bold", color=COLORS["ink"])
    box(
        ax,
        0.710,
        0.385,
        0.245,
        0.125,
        "Rule auditor / conflict arbitrator",
        ["checks citations, HMP rules,", "risk actions and repair logs"],
        fc=COLORS["audit_bg"],
        ec=COLORS["audit"],
        lw=1.1,
    )
    box(
        ax,
        0.710,
        0.205,
        0.245,
        0.120,
        "Priority ladder",
        ["medical red flags > safety > evidence", "protocol > capacity > performance"],
        fc="#ffffff",
        ec="#d1d5db",
        lw=0.7,
    )
    arrow(ax, (0.820, 0.510), (0.820, 0.675), COLORS["audit"], lw=0.9, dashed=True)
    arrow(ax, (0.710, 0.448), (0.660, 0.755), COLORS["audit"], lw=0.8, dashed=True, rad=0.12)
    arrow(ax, (0.833, 0.385), (0.833, 0.325), COLORS["audit"], lw=0.8)

    label(ax, 0.830, 0.145, "Output includes plan, evidence IDs, fired rules, repairs and final audit status.", size=6.3)

    for spine_x in [0.035, 0.675]:
        ax.add_patch(Rectangle((spine_x, 0.135), 0.002, 0.430, facecolor="#e5e7eb", edgecolor="none"))

    fig.savefig(BASE.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(BASE.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(BASE.with_suffix(".tiff"), dpi=600, bbox_inches="tight")
    fig.savefig(BASE.with_suffix(".png"), dpi=240, bbox_inches="tight")


if __name__ == "__main__":
    draw()
