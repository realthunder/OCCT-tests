#!/usr/bin/env python3
# compare.py <before> <after>: two fillet sweeps (drive.py's outdir, or a
# baseline file of "shape case result" lines), the changes classed and listed.
# Status changes are listed in full; among results valid in both, a volume
# moved by more than 1e-9 relative and a tolerance more than halved or doubled
# are counted, and listed SHOW=n of each (default 5).
import glob, os, sys
from collections import Counter


def load(p):
    r = {}
    if os.path.isdir(p):
        for f in glob.glob(os.path.join(p, "*.txt")):
            n = os.path.basename(f)[:-4]
            for l in open(f):
                w = l.split()
                if len(w) == 2:
                    r[n + " " + w[0]] = w[1]
    else:
        for l in open(p):
            w = l.split()
            if len(w) == 3:
                r[w[0] + " " + w[1]] = w[2]
    return r


def parse(x):
    w = x.split(":")
    if len(w) == 4:
        return w[0], float(w[1]), float(w[2]), int(w[3])
    return x, None, None, None


a, b = load(sys.argv[1]), load(sys.argv[2])
show = int(os.environ.get("SHOW", "5"))
common = [k for k in a if k in b]
st = Counter()
moved = {}
for k in sorted(common):
    (sa, va, ta, fa), (sb, vb, tb, fb) = parse(a[k]), parse(b[k])
    st["%s -> %s" % (sa, sb) if sa != sb else sa] += 1
    if sa != sb:
        moved.setdefault("%s -> %s" % (sa, sb), []).append("%s  %s -> %s" % (k, a[k], b[k]))
    elif sa == "ok":
        if abs(va - vb) > 1e-9 * abs(va) or fa != fb:
            moved.setdefault("ok, volume or faces moved", []).append("%s  %s -> %s" % (k, a[k], b[k]))
        elif tb > 2 * ta:
            moved.setdefault("ok, tolerance worse (>2x)", []).append("%s  %.3g -> %.3g" % (k, ta, tb))
        elif tb < ta / 2:
            moved.setdefault("ok, tolerance better (<1/2)", []).append("%s  %.3g -> %.3g" % (k, ta, tb))
print("before %d, after %d, in both %d" % (len(a), len(b), len(common)))
for k, n in sorted(st.items(), key=lambda x: -x[1]):
    print("%7d  %s" % (n, k))
for c, ks in sorted(moved.items(), key=lambda x: -len(x[1])):
    full = "->" in c and "ok," not in c
    print("\n%d %s" % (len(ks), c))
    for k in ks if full else ks[:show]:
        print("    " + k)
