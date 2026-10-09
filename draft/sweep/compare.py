#!/usr/bin/env python3
# compare.py <baseline.txt> <outdir>: drive.py's results against a baseline
# (lines "shape face neutral angle result"), the changes classed and listed.
# A result is ok:volume:faces:bopclean or FAIL(why); volumes within 1e-9
# relative count as the same, changes within 1e-6 are classed together.
import glob, os, sys


def parse(r):
    if r.startswith("ok:") or r.startswith("BAD:"):
        k, v, f, c = r.split(":")[:4]
        return (k, float(v), int(f), int(c))
    return (r,)


def same(a, b):
    if len(a) == 4 and len(b) == 4:
        return a[0] == b[0] and a[2:] == b[2:] and abs(a[1] - b[1]) <= 1e-9 * abs(a[1])
    return a == b


base = {}
for l in open(sys.argv[1]):
    w = l.split()
    if len(w) >= 5:
        base[tuple(w[:4])] = w[4]
new = {}
for f in glob.glob(os.path.join(sys.argv[2], "*.txt")):
    n = os.path.basename(f)[:-4]
    for l in open(f):
        w = l.split()
        if len(w) >= 4 and w[0].isdigit():
            new[(n,) + tuple(w[:3])] = w[3]
missing = [k for k in base if k not in new]
classes = {}
for k in sorted(new):
    if k not in base:
        continue
    a, b = parse(base[k]), parse(new[k])
    if same(a, b):
        continue
    if len(a) == 4 and len(b) == 4:
        dv = abs(a[1] - b[1]) / abs(a[1])
        c = "%s -> %s, volume %s, faces %s, boolean check %s" % (
            a[0], b[0], "same" if dv <= 1e-9 else "within 1e-6" if dv <= 1e-6 else "%.1e rel" % dv,
            "same" if a[2] == b[2] else "%d -> %d" % (a[2], b[2]),
            "same" if a[3] == b[3] else "%d -> %d" % (a[3], b[3]))
    else:
        c = "%s -> %s" % (base[k][:50], new[k][:70])
    classes.setdefault(c, []).append(" ".join(k))
nsame = len(base) - len(missing) - sum(len(v) for v in classes.values())
print("cases %d, run %d, the same %d, missing %d" % (len(base), len(new), nsame, len(missing)))
for c, ks in sorted(classes.items(), key=lambda x: -len(x[1])):
    print("%5d  %s" % (len(ks), c))
    for k in ks[:int(os.environ.get("SHOW", "3"))]:
        print("         " + k)
