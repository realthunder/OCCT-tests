# crease_draw.py <crease.json> <out.png>: sec 74's picture from the file of
# crease_dump.py -- the section of the thick solid at the crease between the
# part's cylinder and its cone, 2 inward and 2 outward, at the fork's offset
# fix levels 3 and 4. Needs matplotlib (the FreeCAD conda env has it).
import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

d = json.load(open(sys.argv[1]))
runs = {(r["value"], r["level"]): r for r in d["runs"]}
fig = plt.figure(figsize=(18, 5.4), dpi=110)
ax = fig.add_subplot(1, 5, 1)
for kind, pts in d["input"]:
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color="#888888", lw=0.8)
for kind, pts in runs[(-2.0, 4)]["section"]:
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color="#1565c0", lw=0.8)
ax.plot([22.5], [8.0], marker="o", ms=9, mfc="none", mec="#d81b60", mew=1.5)
ax.set_aspect("equal")
ax.set_xlim(-1, 27)
ax.set_title("the part's section (grey), 2 inward (blue);\nthe crease, cylinder below, cone "
             "1.5 deg above", fontsize=9)
ax.set_xlabel("x")
ax.set_ylabel("z")
ax.tick_params(labelsize=7)
COLS = {"Cylinder": ("#1565c0", "the cylinder's offset"), "Cone": ("#2e7d32", "the cone's offset")}
panels = (((-2.0, 3), "2 inward, up to level 3"), ((-2.0, 4), "2 inward, level 4"),
          ((2.0, 3), "2 outward, up to level 3"), ((2.0, 4), "2 outward, level 4"))
for k, (key, title) in enumerate(panels):
    r = runs[key]
    ax = fig.add_subplot(1, 5, k + 2)
    cx, cz = (20.5, 8.0) if key[0] < 0 else (24.5, 8.03)
    seen = set()
    for kind, pts in r["section"]:
        near = [p for p in pts if abs(p[0] - cx) < 0.2 and abs(p[1] - cz) < 0.2]
        if not near:
            continue
        col, what = COLS.get(kind, ("#6a1b9a", "the tube round the crease"))
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color=col, lw=1.6,
                label=None if what in seen else what)
        seen.add(what)
        for p in (pts[0], pts[-1]):
            ax.plot([p[0]], [p[1]], marker="s", ms=5, color=col)
    ax.legend(fontsize=7, loc="lower left")
    ax.set_xlim(cx - 0.085, cx + 0.085)
    ax.set_ylim(cz - 0.085, cz + 0.085)
    ax.set_aspect("equal")
    ax.set_title("%s\nvolume %.4f\nwidest gap at an edge's end %.4f" % (
        title, r["volume"], r["gap"]), fontsize=9)
    ax.set_xlabel("x")
    ax.ticklabel_format(useOffset=False, style="plain")
    ax.tick_params(labelsize=7)
    ax.grid(True, lw=0.3, color="#cccccc")
fig.suptitle("#613's part, top and bottom removed: the skin's section where the cylinder's "
             "offset and the cone's meet (squares are the ends of each face's section)",
             fontsize=10)
fig.tight_layout(rect=(0, 0, 1, 0.93))
fig.savefig(sys.argv[2])
