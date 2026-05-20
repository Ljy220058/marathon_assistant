from pathlib import Path
from textwrap import fill

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle


OUT = Path(__file__).resolve().parent
SUBMISSION_OUT = OUT.parent / "submission_package" / "figures"


mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 7.6,
        "axes.linewidth": 0.6,
        "figure.dpi": 180,
    }
)


INK = "#111111"
TEXT = "#333333"
EDGE = "#666f7d"
BOX = "#f7f7f7"
LLM_FILL = "#eeeeee"
RED = "#bf4d4d"
RED_FILL = "#fde6e6"
YELLOW = ("#FFF3CD", "#c8b36c")
GREEN = ("#D4EDDA", "#6aa36a")
MINT = ("#E2F0EA", "#6f9d8b")
BLUE = ("#CCE5FF", "#6e96cf")
PURPLE = ("#E2D9F3", "#9d82b6")


def add_region(ax, x, y, w, h, title, palette, title_dx=0.0, title_dy=0.0):
    face, edge = palette
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.010,rounding_size=0.022",
        linewidth=0.8,
        edgecolor=edge,
        facecolor=face,
        zorder=0,
    )
    ax.add_patch(patch)
    ax.text(
        x + w - 0.018 + title_dx,
        y + h - 0.018 + title_dy,
        title,
        ha="right",
        va="top",
        fontsize=6.8,
        weight="bold",
        color=INK,
        linespacing=0.92,
        bbox={"facecolor": face, "edgecolor": "none", "pad": 0.5},
        zorder=4,
    )
    return patch


def add_box(ax, x, y, w, h, text, fs=7.2, face=BOX, edge=EDGE, dashed=False, lw=0.65):
    rect = Rectangle(
        (x, y),
        w,
        h,
        linewidth=lw,
        edgecolor=edge,
        facecolor=face,
        linestyle=(0, (3.0, 2.0)) if dashed else "solid",
        zorder=2,
    )
    ax.add_patch(rect)
    if text:
        ax.text(
            x + w / 2,
            y + h / 2,
            "\n".join(fill(line, width=22) for line in text.split("\n")),
            ha="center",
            va="center",
            fontsize=fs,
            color=TEXT,
            linespacing=0.94,
            zorder=3,
        )
    return (x, y, w, h)


def add_arrow(ax, start, end, dashed=False, color=INK, rad=0.0, lw=0.78, scale=8):
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=scale,
        linewidth=lw,
        linestyle=(0, (2.5, 2.0)) if dashed else "solid",
        color=color,
        connectionstyle=f"arc3,rad={rad}",
        shrinkA=2.0,
        shrinkB=2.0,
        zorder=1,
    )
    ax.add_patch(arrow)


def add_elbow(ax, points, dashed=False, color=INK, lw=0.78, scale=8):
    """Draw an orthogonal connector and keep the arrow head on the final leg."""
    if len(points) < 2:
        return
    linestyle = (0, (2.5, 2.0)) if dashed else "solid"
    for a, b in zip(points[:-2], points[1:-1]):
        ax.plot(
            [a[0], b[0]],
            [a[1], b[1]],
            color=color,
            linewidth=lw,
            linestyle=linestyle,
            zorder=1,
            solid_capstyle="butt",
        )
    add_arrow(ax, points[-2], points[-1], dashed=dashed, color=color, lw=lw, scale=scale)


def left(b):
    x, y, _, h = b
    return x, y + h / 2


def right(b):
    x, y, w, h = b
    return x + w, y + h / 2


def top(b):
    x, y, w, h = b
    return x + w / 2, y + h


def bottom(b):
    x, y, w, _ = b
    return x + w / 2, y


def save_all(fig):
    bases = [
        OUT / "rule_governed_workflow",
        OUT / "rule_governed_workflow_evidence_bounded",
        SUBMISSION_OUT / "rule_governed_workflow",
        SUBMISSION_OUT / "rule_governed_workflow_evidence_bounded",
    ]
    SUBMISSION_OUT.mkdir(parents=True, exist_ok=True)
    for base in bases:
        fig.savefig(base.with_suffix(".svg"), bbox_inches="tight")
        fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight")
        fig.savefig(base.with_suffix(".png"), dpi=300, bbox_inches="tight")


def add_arrow_legend(ax, x=0.705, y=0.900):
    patch = FancyBboxPatch(
        (x, y),
        0.220,
        0.104,
        boxstyle="round,pad=0.006,rounding_size=0.006",
        linewidth=0.55,
        edgecolor="#d0d0d0",
        facecolor="#ffffff",
        zorder=0.5,
    )
    ax.add_patch(patch)
    add_arrow(ax, (x + 0.010, y + 0.085), (x + 0.046, y + 0.085), lw=0.62, scale=5)
    ax.text(x + 0.052, y + 0.085, "main/control flow", ha="left", va="center", fontsize=4.2, color=TEXT, zorder=6)
    add_arrow(ax, (x + 0.010, y + 0.068), (x + 0.046, y + 0.068), dashed=True, color=EDGE, lw=0.62, scale=5)
    ax.text(x + 0.052, y + 0.068, "LLM/optional path", ha="left", va="center", fontsize=4.2, color=TEXT, zorder=6)
    add_arrow(ax, (x + 0.010, y + 0.051), (x + 0.046, y + 0.051), color=RED, lw=0.68, scale=5)
    ax.text(x + 0.052, y + 0.051, "safety refusal path", ha="left", va="center", fontsize=4.2, color=TEXT, zorder=6)
    ax.text(
        x + 0.010,
        y + 0.023,
        "RiskGate: R3 refuse; R2 downgrade\nR1 allow; R0 explain",
        ha="left",
        va="center",
        fontsize=3.6,
        color=TEXT,
        zorder=6,
    )


def draw():
    fig = plt.figure(figsize=(6.95, 5.28))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.085)
    ax.axis("off")

    # 1. Inputs.
    add_region(ax, 0.04, 0.820, 0.86, 0.135, "Case inputs", YELLOW)
    query = add_box(ax, 0.075, 0.878, 0.130, 0.045, "User query")
    visible = add_box(ax, 0.265, 0.858, 0.270, 0.072, "System-visible\ncase data", fs=6.5)
    add_box(ax, 0.575, 0.852, 0.150, 0.046, "Evaluator-only\nlabels (hidden)", fs=5.8, face="#ffffff", edge=RED, dashed=True)
    add_arrow(ax, right(query), left(visible))
    add_arrow_legend(ax, 0.680, 0.972)

    # 2. Triage.
    add_region(ax, 0.08, 0.653, 0.84, 0.125, "Triage", GREEN, title_dx=0.012, title_dy=0.014)
    input_filter = add_box(ax, 0.190, 0.707, 0.130, 0.043, "Input\nfilter")
    risk = add_box(
        ax,
        0.360,
        0.707,
        0.145,
        0.043,
        "RiskGate\n(R0-R3 triage)",
        fs=6.3,
    )
    evidence = add_box(ax, 0.545, 0.707, 0.145, 0.043, "EvidenceGate")
    contract = add_box(ax, 0.730, 0.707, 0.150, 0.043, "Prescription\nContract")
    stop = add_box(ax, 0.405, 0.659, 0.240, 0.030, "Clarify or refuse", fs=6.2, edge=RED, dashed=True)
    add_elbow(ax, [bottom(visible), (bottom(visible)[0], 0.793), (top(input_filter)[0], 0.793), top(input_filter)])
    add_arrow(ax, right(input_filter), left(risk))
    add_arrow(ax, right(risk), left(evidence))
    add_arrow(ax, right(evidence), left(contract))
    add_arrow(ax, (risk[0] + risk[2] * 0.55, risk[1]), (stop[0] + stop[2] * 0.35, stop[1] + stop[3]), color=RED, lw=0.85)
    add_arrow(ax, (evidence[0] + evidence[2] * 0.40, evidence[1]), (stop[0] + stop[2] * 0.70, stop[1] + stop[3]), color=RED, lw=0.85)

    # 3. Construction.
    add_region(ax, 0.09, 0.421, 0.82, 0.190, "Construction", MINT)
    goal = add_box(ax, 0.410, 0.534, 0.150, 0.039, "Goal and\nphase")
    actions = add_box(ax, 0.600, 0.534, 0.150, 0.039, "Approved\nactions")
    coach = add_box(
        ax,
        0.600,
        0.486,
        0.165,
        0.039,
        "Coach draft\nwithin contract",
        fs=6.8,
        face=LLM_FILL,
        dashed=True,
        lw=0.85,
    )
    experts = add_box(ax, 0.800, 0.486, 0.095, 0.039, "Conditional\nexperts", fs=6.0)
    candidate = add_box(ax, 0.520, 0.431, 0.250, 0.035, "Candidate prescription + trace", fs=6.4)
    add_elbow(
        ax,
        [
            bottom(contract),
            (bottom(contract)[0], 0.588),
            (actions[0] - 0.030, 0.588),
            (actions[0] - 0.030, left(actions)[1]),
            left(actions),
        ],
    )
    add_arrow(ax, right(goal), left(actions))
    add_arrow(ax, bottom(actions), top(coach), dashed=True, color=EDGE)
    add_arrow(ax, right(coach), left(experts), dashed=True, color=EDGE)
    add_arrow(ax, bottom(coach), top(candidate), dashed=True, color=EDGE)

    # 4. Audit and repair.
    add_region(ax, 0.10, 0.234, 0.80, 0.145, "Audit / repair", BLUE)
    auditor = add_box(ax, 0.430, 0.291, 0.155, 0.040, "Rule Auditor")
    repair = add_box(ax, 0.650, 0.291, 0.155, 0.040, "Bounded\nrepair")
    reaudit = add_box(ax, 0.430, 0.246, 0.155, 0.040, "Re-audit")
    refusal = add_box(
        ax,
        0.650,
        0.246,
        0.155,
        0.031,
        "Fail-closed refusal",
        fs=6.5,
        face=RED_FILL,
        edge=RED,
        lw=0.95,
    )
    add_elbow(ax, [bottom(candidate), (bottom(candidate)[0], 0.397), (top(auditor)[0], 0.397), top(auditor)])
    add_arrow(ax, right(auditor), left(repair))
    add_elbow(ax, [left(reaudit), (0.405, left(reaudit)[1]), (0.405, left(auditor)[1]), left(auditor)], lw=0.70, scale=6)
    add_arrow(ax, (repair[0], repair[1] + repair[3] * 0.24), (right(reaudit)[0], right(reaudit)[1]), rad=-0.10)
    add_arrow(ax, bottom(repair), top(refusal), color=RED, lw=1.05, scale=9)
    add_elbow(ax, [top(repair), (top(repair)[0], 0.396), (bottom(candidate)[0], 0.396), bottom(candidate)], dashed=True, color=EDGE, lw=0.70)

    # 5. Outputs.
    add_region(ax, 0.14, 0.065, 0.78, 0.125, "Outputs", PURPLE)
    answer = add_box(ax, 0.245, 0.105, 0.145, 0.038, "Final answer")
    trace = add_box(ax, 0.435, 0.105, 0.140, 0.038, "Audit trace")
    summary = add_box(ax, 0.620, 0.105, 0.145, 0.038, "Result summary", fs=6.1)
    evaluator = add_box(ax, 0.805, 0.105, 0.110, 0.038, "Evaluator", fs=6.2)
    add_elbow(ax, [bottom(reaudit), (bottom(reaudit)[0], 0.245), (top(answer)[0], 0.245), top(answer)])
    add_elbow(ax, [left(stop), (0.165, left(stop)[1]), (0.165, left(answer)[1]), left(answer)], color=RED, lw=0.72, scale=7)
    add_elbow(ax, [bottom(refusal), (bottom(refusal)[0], 0.245), (top(answer)[0] + 0.030, 0.245), (top(answer)[0] + 0.030, top(answer)[1])], color=RED, lw=0.85, scale=8)
    add_arrow(ax, right(answer), left(trace))
    add_arrow(ax, right(trace), left(summary))
    add_arrow(ax, right(summary), left(evaluator))

    save_all(fig)


if __name__ == "__main__":
    draw()
