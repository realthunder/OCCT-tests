#!/usr/bin/env python3
# compare.py <before> <after>: two fillet sweeps (drive.py's outdir, or a
# baseline file of "shape case result" lines), the changes classed and listed.
# Status changes are listed in full; among results valid in both, a volume
# moved by more than 1e-9 relative and a tolerance more than halved or doubled
# are counted, and listed SHOW=n of each (default 5).
# fsw_bop.py's results (BOP's verdict after the fourth field) are compared the
# same way, and the cases whose verdict changed are listed in full.
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
    if len(w) >= 4 and w[0] in ("ok", "BAD", "LOOSE"):
        return w[0], float(w[1]), float(w[2]), int(w[3])
    return x, None, None, None


def bop(x):
    """BOP's verdict of an fsw_bop.py result: "clean", "reported" or None."""
    w = x.split(":")
    if len(w) >= 5 and w[0] == "ok":
        return "clean" if w[4] == "c" else "reported"
    return None


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
        ba, bb = bop(a[k]), bop(b[k])
        if ba and bb and ba != bb:
            moved.setdefault("BOP's check %s -> %s" % (ba, bb), []).append("%s  %s -> %s" % (k, a[k], b[k]))
print("before %d, after %d, in both %d" % (len(a), len(b), len(common)))
for k, n in sorted(st.items(), key=lambda x: -x[1]):
    print("%7d  %s" % (n, k))
for c, ks in sorted(moved.items(), key=lambda x: -len(x[1])):
    full = "->" in c and not c.startswith("ok,")
    print("\n%d %s" % (len(ks), c))
    for k in ks if full else ks[:show]:
        print("    " + k)
