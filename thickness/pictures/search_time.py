"""The figure of sec 64: #360's plate, its top removed 1 to 5 inward
(Arc join, intersection on), the seconds one thickness takes -- upstream,
the fork before sec 64 and after it. The numbers are measured by hand with
corpus/tools/thk, each run alone (README sec 64); run this with the FreeCAD
conda env's python to draw them again:

    python pictures/search_time.py models/pictures/issue360_plate_search_time.png
"""
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEPTHS = ["1", "2", "3", "4", "5"]
UPSTREAM = [0.8, 0.8, 0.7, 0.7, 0.7]
BEFORE = [16.0, 43.6, 20.3, 23.0, 145.9]
AFTER = [3.8, 5.9, 6.7, 6.1, 7.5]

fig, ax = plt.subplots(figsize=(9.6, 4.6), dpi=150)
width = 0.26
xs = range(len(DEPTHS))
series = (("upstream OCCT 8.0.1 (invalid at 2)", UPSTREAM, "#9aa6b6"),
          ("fork before (7b20287a74)", BEFORE, "#c0504d"),
          ("fork after", AFTER, "#4f81bd"))
for k, (label, values, color) in enumerate(series):
    bars = ax.bar([x + (k - 1) * width for x in xs], values, width, label=label, color=color)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value * 1.08, "%.1f" % value, ha="center",
                va="bottom", fontsize=8)
ax.set_yscale("log")
ax.set_ylim(0.4, 400)
ax.set_xticks(list(xs))
ax.set_xticklabels(DEPTHS)
ax.set_xlabel("thickness inward")
ax.set_ylabel("seconds (log scale)")
ax.set_title("#360's plate, its top removed: time of one thickness", fontsize=11, loc="left")
ax.legend(frameon=False, fontsize=9, loc="upper left")
for side in ("top", "right"):
    ax.spines[side].set_visible(False)
fig.tight_layout()
fig.savefig(sys.argv[1])
