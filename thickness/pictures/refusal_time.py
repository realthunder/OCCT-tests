"""The figure of sec 65: #613's model, its side (face 1) removed -- the
seconds one thickness takes to be refused, the fork before sec 65 and after
it. Upstream refuses all eight at once (a shell not connected). The numbers
are measured by hand with corpus/tools/thk, each run alone (README sec 65);
run this with the FreeCAD conda env's python to draw them again:

    python pictures/refusal_time.py models/pictures/issue613_side_refusal_time.png
"""
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

RUNS = ["1 out\nArc", "1 in\nArc", "0.5 out\nArc", "0.5 in\nArc",
        "1 out\nInters.", "1 in\nInters.", "0.5 out\nInters.", "0.5 in\nInters."]
BEFORE = [0.4, 20.3, 0.5, 24.2, 60.6, 80.6, 3.4, 27.2]
AFTER = [0.4, 3.4, 0.5, 3.4, 4.0, 5.4, 3.9, 6.6]

fig, ax = plt.subplots(figsize=(9.6, 4.6), dpi=150)
width = 0.36
xs = range(len(RUNS))
series = (("fork before sec 65", BEFORE, "#c0504d"),
          ("fork after", AFTER, "#4f81bd"))
for k, (label, values, color) in enumerate(series):
    bars = ax.bar([x + (k - 0.5) * width for x in xs], values, width, label=label, color=color)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value * 1.08, "%.1f" % value, ha="center",
                va="bottom", fontsize=8)
ax.set_yscale("log")
ax.set_ylim(0.2, 300)
ax.set_xticks(list(xs))
ax.set_xticklabels(RUNS, fontsize=8)
ax.set_ylabel("seconds (log scale)")
ax.set_title("#613's model, its side removed: time of one thickness, refused", fontsize=11,
             loc="left")
ax.legend(frameon=False, fontsize=9, loc="upper left")
for side in ("top", "right"):
    ax.spines[side].set_visible(False)
fig.tight_layout()
fig.savefig(sys.argv[1])
