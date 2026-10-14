#!/usr/bin/env python3
# bopcmp.py <outdir>: fsw_bop.py's results classed -- per shape, the valid
# results BOP's check takes and the ones it reports, those by what it reports
# and by tolerance: a result at 1e-4 or less that fails the check has a fault
# of its geometry, a loose one may only be loose. The reported cases are
# listed, SHOW of each shape (default 400); TIGHT=1 lists the tight ones only.
import glob, os, sys
from collections import Counter, defaultdict

d = sys.argv[1]
show = int(os.environ.get("SHOW", "400"))
tight = os.environ.get("TIGHT") == "1"
rows = []
allk = Counter()
other = Counter()
for f in sorted(glob.glob(os.path.join(d, "*.txt"))):
    n = os.path.basename(f)[:-4]
    c = Counter()
    kinds = Counter()
    lst = []
    for l in open(f):
        w = l.split()
        if len(w) != 2:
            continue
        x = w[1].split(":")
        if x[0] != "ok" or len(x) < 5:
            other[x[0]] += 1
            c[x[0]] += 1
            continue
        if x[4] == "c":
            c["clean"] += 1
            continue
        t = float(x[2])
        c["tight" if t <= 1e-4 else "loose"] += 1
        ks = [k.split("*")[0] for k in x[5].split(",")] if len(x) > 5 and x[5] else ["?"]
        for k in ks:
            kinds[k] += 1
            allk[k] += 1
        if t <= 1e-4 or not tight:
            lst.append("    %-22s tol %-8s %s" % (w[0], x[2], x[5] if len(x) > 5 else ""))
    rows.append((n, c, kinds, lst))
print("%-22s %6s %6s %6s   %s" % ("shape", "clean", "tight", "loose", "other"))
tot = Counter()
for n, c, kinds, lst in rows:
    tot.update(c)
    o = " ".join("%s %d" % (k, v) for k, v in sorted(c.items()) if k not in ("clean", "tight", "loose", "skip"))
    print("%-22s %6d %6d %6d   %s" % (n, c["clean"], c["tight"], c["loose"], o))
print("%-22s %6d %6d %6d" % ("all", tot["clean"], tot["tight"], tot["loose"]))
print("\nreported, by kind (cases):")
for k, v in sorted(allk.items(), key=lambda x: -x[1]):
    print("%7d  %s" % (v, k))
for n, c, kinds, lst in rows:
    if lst:
        print("\n%s: %s" % (n, ", ".join("%s %d" % x for x in sorted(kinds.items(), key=lambda x: -x[1]))))
        for x in lst[:show]:
            print(x)
