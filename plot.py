"""
Plot Political Compass results from one or more JSON result files.

Usage:
    python plot.py results.json [results2.json ...]
    python plot.py results/*.json --output compass.png
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
except ImportError:
    sys.exit("matplotlib not found — run: pip install matplotlib")


QUADRANT_COLORS = {
    "Left-Libertarian":    "#a8d8a8",
    "Right-Libertarian":   "#a8c8e8",
    "Left-Authoritarian":  "#f4a8a8",
    "Right-Authoritarian": "#f4d8a8",
}

QUADRANT_LABELS = {
    "Left-Libertarian":    ("LEFT\nLIBERTARIAN",   -7.5, -7.5),
    "Right-Libertarian":   ("RIGHT\nLIBERTARIAN",   7.5, -7.5),
    "Left-Authoritarian":  ("LEFT\nAUTHORITARIAN",  -7.5,  7.5),
    "Right-Authoritarian": ("RIGHT\nAUTHORITARIAN",  7.5,  7.5),
}


def load_result(path: Path) -> dict:
    data = json.loads(path.read_text())
    coords = data["coordinates"]
    return {
        "label": data.get("label") or data["model"].split("/")[-1],
        "model": data["model"],
        "style": data.get("style"),
        "economic": coords["economic"],
        "social": coords["social"],
        "economic_std": coords.get("economic_std"),
        "social_std": coords.get("social_std"),
    }


def plot(points: list[dict], output: str | None) -> None:
    fig, ax = plt.subplots(figsize=(8, 8))

    # Quadrant backgrounds
    ax.axhspan(0, 10,  xmin=0,   xmax=0.5, color=QUADRANT_COLORS["Left-Authoritarian"],  zorder=0)
    ax.axhspan(0, 10,  xmin=0.5, xmax=1,   color=QUADRANT_COLORS["Right-Authoritarian"], zorder=0)
    ax.axhspan(-10, 0, xmin=0,   xmax=0.5, color=QUADRANT_COLORS["Left-Libertarian"],    zorder=0)
    ax.axhspan(-10, 0, xmin=0.5, xmax=1,   color=QUADRANT_COLORS["Right-Libertarian"],   zorder=0)

    # Axes
    ax.axhline(0, color="white", linewidth=1.5, zorder=1)
    ax.axvline(0, color="white", linewidth=1.5, zorder=1)

    # Quadrant labels
    for _, (text, x, y) in QUADRANT_LABELS.items():
        ax.text(x, y, text, ha="center", va="center",
                fontsize=8, color="white", alpha=0.6, fontweight="bold", zorder=2)

    # Data points. Instruction-tuned checkpoints get a distinct marker so the
    # pretraining comparison (base vs base) stays readable at a glance.
    colors = plt.cm.tab10.colors
    markers = {"it": "^", "base": "o"}
    placed: list[tuple[float, float]] = []

    for i, pt in enumerate(points):
        color = colors[i % len(colors)]
        x, y = pt["economic"], pt["social"]

        if pt["economic_std"]:
            ax.errorbar(
                x, y,
                xerr=pt["economic_std"], yerr=pt["social_std"],
                fmt="none", color=color, alpha=0.5, capsize=4, zorder=3,
            )
        ax.scatter(x, y, s=140, color=color, marker=markers.get(pt.get("style"), "o"),
                   zorder=4, edgecolors="white", linewidths=0.8)

        # Nudge the label if it would land on top of an earlier one.
        dx, dy = 8, 4
        for px, py in placed:
            if abs(x - px) < 2.2 and abs(y - py) < 1.1:
                dy = -14 if dy > 0 else dy - 14
        placed.append((x, y))

        label = pt["label"]
        if pt.get("style"):
            label = f"{label} ({pt['style']})"
        ax.annotate(
            label, (x, y),
            textcoords="offset points", xytext=(dx, dy),
            fontsize=9, color=color, fontweight="bold", zorder=5,
        )

    ax.set_xlim(-10, 10)
    ax.set_ylim(-10, 10)
    ax.set_xlabel("Economic axis  (← Left / Right →)", fontsize=11)
    ax.set_ylabel("Social axis  (← Libertarian / Authoritarian →)", fontsize=11)
    ax.set_title("Political Compass", fontsize=14, fontweight="bold")
    ax.set_facecolor("#e8e8e8")
    fig.patch.set_facecolor("#f8f8f8")
    ax.grid(color="white", linewidth=0.5, zorder=1)

    plt.tight_layout()
    if output:
        fig.savefig(output, dpi=150)
        print(f"Saved to {output}")
    else:
        plt.show()


def main():
    parser = argparse.ArgumentParser(description="Plot Political Compass results")
    parser.add_argument("results", nargs="+", help="JSON result file(s) from evaluate.py")
    parser.add_argument("--output", default=None, help="Save plot to this path (e.g. compass.png)")
    args = parser.parse_args()

    points = [load_result(Path(p)) for p in args.results]
    plot(points, args.output)


if __name__ == "__main__":
    main()
