#!/usr/bin/env python3
# refcmp.py <outdir>: fsw_ref.py's results classed -- valid on both and the
# same; the volume different (by more than VOL, default 1e-6, relative);
# BOP's check failing in pieces only, refined only, on both; the tolerance
# more than ten times the refined shape's and above 1e-4; and every other
# pair of statuses. The cases of each class but the dull ones are listed,
# SHOW of them (default 400).
# A volume that differs by 1e-5 or less under tight tolerances can be the
# integration's: the same face trimmed by a B-spline, parametrized the other
# way round, gave 107.9625 and 107.9723 of area (#962's chamfer input, edge
# 12 at 2; the two faces within 1e-10 of one another).
import glob, os, sys
from collections import Counter, defaultdict
d = sys.argv[1]
vtol = float(os.environ.get("VOL", "1e-6"))
show = int(os.environ.get("SHOW", "400"))
cnt = Counter(); lst = defaultdict(list)
def parse(x):
    w = x.split(":")
    if w[0] in ("ok", "LOOSE", "BAD"): return w[0], float(w[1]), float(w[2]), w[3], (w[4] if len(w) > 4 else "")
    return w[0], None, None, None, (w[1] if len(w) > 1 else "")
for f in sorted(glob.glob(os.path.join(d, "*.txt"))):
    n = os.path.basename(f)[:-4]
    for l in open(f):
        w = l.split()
        if len(w) != 2: continue
        if "|" not in w[1]:
            cnt[w[1]] += 1; continue
        a, b = w[1].split("|")
        (sa, va, ta, ba, _), (sb, vb, tb, bb, nb) = parse(a), parse(b)
        part = nb and nb.split("/")[0] != nb.split("/")[1]
        key = None
        if sa == "ok" and sb == "ok":
            if part: key = "both ok, a split among the edges"
            elif abs(va - vb) > vtol * abs(vb): key = "both ok, VOLUME differs"
            elif ba == "b" and bb == "c": key = "both ok, BOP fails only in pieces"
            elif ba == "c" and bb == "b": key = "both ok, BOP fails only refined"
            elif ba == "b" and bb == "b": key = "both ok, BOP fails on both"
            elif ta > 1e-4 and ta > 10 * tb: key = "both ok, TOLERANCE worse in pieces (>10x, >1e-4)"
            elif tb > 1e-4 and tb > 10 * ta: key = "both ok, tolerance worse refined"
            else: key = "both ok, same"
        else:
            key = "%s | %s%s" % (sa, sb, " (split among the edges)" if part else "")
        cnt[key] += 1
        lst[key].append("%s %s  %s | %s" % (n, w[0], a, b))
for k, c in sorted(cnt.items(), key=lambda x: -x[1]): print("%7d  %s" % (c, k))
for k in sorted(lst):
    if k in ("both ok, same", "EXC | EXC", "BAD | BAD", "both ok, BOP fails on both") or "noedge" in k: continue
    print("\n%d %s" % (len(lst[k]), k))
    for x in lst[k][:show]: print("   ", x)
