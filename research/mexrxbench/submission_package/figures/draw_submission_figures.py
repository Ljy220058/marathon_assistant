from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch


OUT = Path(__file__).resolve().parent

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 8,
        "axes.linewidth": 0.6,
    }
)

COL = {
    "text": "#333333",
    "line": "#8a8f96",
    "arrow": "#444444",
    "muted": "#f5f6f7",
    "case": "#FFF3CD",
    "rule": "#D4EDDA",
    "audit": "#CCE5FF",
    "output": "#E2D9F3",
    "accent": "#b97a2c",
    "hidden": "#a55f5f",
    "red": "#bf4d4d",
    "dash": "#6e6e6e",
}


def setup(width=10.6, height=6.4):
    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


def rounded(ax, xy, w, h, fc="white", ec=None, lw=1.0, r=0.018, ls="-"):
    patch = FancyBboxPatch(
        xy,
        w,
        h,
        boxstyle=f"round,pad=0.006,rounding_size={r}",
        facecolor=fc,
        edgecolor=ec or COL["line"],
        linewidth=lw,
        linestyle=ls,
    )
    ax.add_patch(patch)
    return patch


def box(ax, x, y, w, h, text, fc="white", ec=None, lw=0.9, size=7.4, weight="normal", ls="-"):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec or COL["line"], linewidth=lw, linestyle=ls))
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        color=COL["text"],
        fontsize=size,
        fontweight=weight,
        linespacing=0.9,
    )


def band(ax, y, h, title, fc):
    rounded(ax, (0.055, y), 0.89, h, fc=fc, ec="#c2c6ca", lw=1.0, r=0.02)
    ax.text(0.075, y + h - 0.026, title, ha="left", va="top", fontsize=7.4, fontweight="bold", color="#555555")


def arrow(ax, start, end, color=None, lw=1.1, ls="-", rad=0.0, ms=9):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=ms,
            linewidth=lw,
            color=color or COL["arrow"],
            linestyle=ls,
            connectionstyle=f"arc3,rad={rad}",
        )
    )


def elbow(ax, points, color=None, lw=1.1, ls="-", ms=9):
    if len(points) < 2:
        return
    c = color or COL["arrow"]
    for a, b in zip(points[:-2], points[1:-1]):
        ax.plot([a[0], b[0]], [a[1], b[1]], color=c, linewidth=lw, linestyle=ls, solid_capstyle="butt")
    arrow(ax, points[-2], points[-1], color=c, lw=lw, ls=ls, ms=ms)


def label(ax, x, y, text, size=7.2, color=None, weight="normal", ha="center"):
    ax.text(x, y, text, ha=ha, va="center", fontsize=size, color=color or COL["text"], fontweight=weight)


def save(fig, name):
    for ext, kwargs in {
        "svg": {},
        "pdf": {},
        "png": {"dpi": 450},
    }.items():
        fig.savefig(OUT / f"{name}.{ext}", bbox_inches="tight", pad_inches=0.05, **kwargs)
    plt.close(fig)


def arrow_legend(ax, x=0.745, y=0.680):
    rounded(ax, (x, y), 0.158, 0.064, fc="#ffffff", ec="#d0d0d0", lw=0.50, r=0.005)
    arrow(ax, (x + 0.010, y + 0.049), (x + 0.042, y + 0.049), lw=0.65, ms=5)
    label(ax, x + 0.049, y + 0.049, "main/control", size=4.7, ha="left")
    arrow(ax, (x + 0.010, y + 0.033), (x + 0.042, y + 0.033), lw=0.65, ls="--", color=COL["dash"], ms=5)
    label(ax, x + 0.049, y + 0.033, "LLM/optional", size=4.7, ha="left")
    arrow(ax, (x + 0.010, y + 0.017), (x + 0.042, y + 0.017), lw=0.70, color=COL["red"], ms=5)
    label(ax, x + 0.049, y + 0.017, "safety refusal", size=4.7, ha="left")


def benchmark_split():
    fig, ax = setup(10.8, 5.15)

    band(ax, 0.74, 0.16, "Case inputs", COL["case"])
    box(ax, 0.095, 0.795, 0.14, 0.048, "User query")
    box(ax, 0.310, 0.785, 0.22, 0.068, "System-visible\ncase data", size=7.0)
    box(ax, 0.715, 0.795, 0.18, 0.048, "Evaluator-only\nlabels (hidden)", size=7.0, ec=COL["hidden"], ls="--")
    arrow(ax, (0.235, 0.819), (0.310, 0.819))

    band(ax, 0.52, 0.16, "Solver-visible flow", COL["rule"])
    box(ax, 0.430, 0.568, 0.22, 0.078, "Solvers\n(reference + baselines)", size=7.0)
    box(ax, 0.790, 0.580, 0.13, 0.052, "Candidate\noutputs + traces", size=6.8)
    arrow(ax, (0.650, 0.606), (0.790, 0.606))
    arrow(ax, (0.420, 0.785), (0.540, 0.646))

    band(ax, 0.30, 0.16, "Evaluation", COL["audit"])
    box(ax, 0.715, 0.360, 0.18, 0.052, "Gold split\nheld out", size=7.0, ec=COL["hidden"], ls="--")
    box(ax, 0.455, 0.360, 0.18, 0.052, "Evaluator")
    box(ax, 0.175, 0.350, 0.17, 0.072, "Metrics\nstatus, risk, support,\nunsafe, trace", size=7.0)
    elbow(ax, [(0.855, 0.580), (0.855, 0.480), (0.545, 0.480), (0.545, 0.412)])
    arrow(ax, (0.455, 0.386), (0.345, 0.386))

    rounded(ax, (0.23, 0.13), 0.54, 0.08, fc="#fafafa", ec="#b7b7b7", lw=0.9, r=0.012, ls="--")
    label(ax, 0.50, 0.17, "Hard-100 stress set reported separately; not merged into default score", size=7.2)
    arrow_legend(ax, 0.740, 0.915)

    save(fig, "benchmark_split_evaluation_protocol")


def trace_decision():
    fig, ax = setup(10.0, 6.3)
    label(ax, 0.50, 0.965, "Single-case decision flow", size=8.4, weight="bold")

    band(ax, 0.76, 0.16, "(a) Inputs", COL["case"])
    box(ax, 0.120, 0.812, 0.18, 0.052, "System-visible case", size=7.0)
    box(ax, 0.390, 0.812, 0.17, 0.052, "Request\neducation scope", size=7.0)
    arrow(ax, (0.300, 0.838), (0.390, 0.838))

    band(ax, 0.52, 0.17, "(b) Rule checks", COL["rule"])
    box(ax, 0.140, 0.585, 0.16, 0.052, "RiskGate\nR0")
    box(ax, 0.350, 0.585, 0.17, 0.052, "EvidenceGate\nHMP types")
    box(ax, 0.565, 0.585, 0.18, 0.052, "Prescription Contract\n(education only)", size=6.2)
    box(ax, 0.795, 0.585, 0.12, 0.052, "Audit\npass")
    arrow(ax, (0.300, 0.611), (0.350, 0.611))
    arrow(ax, (0.520, 0.611), (0.565, 0.611))
    arrow(ax, (0.745, 0.611), (0.795, 0.611))
    elbow(ax, [(0.475, 0.812), (0.475, 0.715), (0.220, 0.715), (0.220, 0.637)])

    band(ax, 0.29, 0.16, "(c) Trace requirements", COL["audit"])
    box(ax, 0.145, 0.342, 0.18, 0.058, "Rules fired", size=7.0)
    box(ax, 0.410, 0.342, 0.18, 0.058, "Grounding IDs", size=7.0)
    box(ax, 0.700, 0.342, 0.17, 0.058, "Final trace\nstatus=answered", size=7.0)
    arrow(ax, (0.325, 0.371), (0.410, 0.371))
    arrow(ax, (0.590, 0.371), (0.700, 0.371))
    elbow(ax, [(0.855, 0.585), (0.855, 0.480), (0.235, 0.480), (0.235, 0.400)])

    band(ax, 0.08, 0.13, "Output", COL["output"])
    box(ax, 0.220, 0.124, 0.18, 0.048, "Final answer")
    box(ax, 0.480, 0.124, 0.18, 0.048, "Audit trace")
    box(ax, 0.730, 0.124, 0.16, 0.048, "Evaluator")
    arrow(ax, (0.400, 0.148), (0.480, 0.148))
    arrow(ax, (0.660, 0.148), (0.730, 0.148))
    elbow(ax, [(0.785, 0.342), (0.785, 0.245), (0.570, 0.245), (0.570, 0.172)])
    arrow_legend(ax, 0.745, 0.865)

    save(fig, "trace_governed_decision_example")


if __name__ == "__main__":
    benchmark_split()
    trace_decision()
