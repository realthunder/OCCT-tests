# fsw.py's cases, the valid results put to BOP's argument check (Part's
# check(True)): BRepCheck's "valid" is not what the next boolean asks for.
# Run by drive.py with WORKER=fsw_bop.py.
# env: as fsw.py, plus NAME (the shape's name in shapes.lst), SKIP, a
#      baseline file -- the shape's cases not valid there are not run
#      ("skip") --, and INPUTS (default baseline/inputs_bop.txt, bopin.py's):
#      the cases of an input that fails the check itself are "input".
#      FLAT as fsw.py's.
# A result is fsw.py's with :c (nothing reported) or :b:<what> added to a
# valid one, <what> being <shape type>/<BOP's status>*<count>,... A check
# that outlasts drive.py's TIMEOUT leaves the case TIMEOUT.
# bopcmp.py classes the results.
import itertools, os, sys
import Part

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from flat_end import set_flat_end  # noqa: E402

if os.environ.get("FLAT", "0") != "0":
    set_flat_end(True)

def emit(s):
    os.write(1, ("\n" + s + "\n").encode())


def bop(s):
    try:
        s.check(True)
        return "c"
    except Exception as e:
        n = {}
        for l in str(e).split("\n"):
            if l.strip().startswith("Error in "):
                t, k = l.strip()[9:].split(":", 1)
                k = t.strip() + "/" + k.replace("BOPAlgo", "").replace("_", "").replace(" ", "")
                n[k] = n.get(k, 0) + 1
        return "b:" + ",".join("%s*%d" % x for x in sorted(n.items()))


mode = os.environ.get("MODE", "edge")
start = int(os.environ.get("START", "0"))
radii = [float(x) for x in os.environ.get("RADII", "0.3 0.8 2" if mode == "edge" else "0.3 1").split()]
name = os.environ["NAME"]
sweep = os.environ.get("SWEEP", os.path.expanduser("~/works/sw/occt/tests/fork/fillet/sweep"))
run = set()
for l in open(os.environ["SKIP"]):
    w = l.split()
    if len(w) == 3 and w[0] == name and w[2].startswith("ok:"):
        run.add(w[1])
inbad = False
for l in open(os.environ.get("INPUTS", os.path.join(sweep, "baseline", "inputs_bop.txt"))):
    w = l.split()
    if len(w) == 2 and w[0] == name and w[1] != "clean":
        inbad = True
s = Part.read(os.environ["SHAPE"])
brep = s.exportBrepToString()
edges = s.Edges


def free(e):
    return not e.Degenerated and len(s.ancestorsOfType(e, Part.Face)) == 2


cases = []
if mode == "edge":
    for i, e in enumerate(edges, 1):
        if free(e):
            cases += [("E%d@%g" % (i, r), (i,), r) for r in radii]
else:
    for vi, v in enumerate(s.Vertexes, 1):
        es = [e for e in s.ancestorsOfType(v, Part.Edge) if free(e)]
        if len(es) < 3:
            continue
        idx = [next(i for i, x in enumerate(edges, 1) if x.isSame(e)) for e in es]
        sets = [tuple(idx)] + list(itertools.combinations(idx, 2)) + [(i,) for i in idx]
        for st in sets:
            cases += [("V%d:%s@%g" % (vi, ",".join(map(str, st)), r), st, r) for r in radii]
emit("N %d" % len(cases))
for n in range(start, len(cases)):
    key, st, r = cases[n]
    emit("T %d %s" % (n, key))
    if key not in run or inbad:
        emit("%d %s %s" % (n, key, "skip" if key not in run else "input"))
        continue
    x = Part.Shape()
    x.importBrepFromString(brep, False)
    try:
        f = x.makeFillet(r, [x.Edges[i - 1] for i in st])
        if f.isNull():
            res = "NULL"
        else:
            tol = max([y.Tolerance for y in f.Edges] + [y.Tolerance for y in f.Vertexes])
            res = "%s:%.10g:%.3g:%d" % ("ok" if f.isValid() else "BAD", f.Volume, tol, len(f.Faces))
            if f.isValid():
                res += ":" + bop(f)
    except Exception:
        res = "EXC"
    emit("%d %s %s" % (n, key, res))
emit("DONE")
