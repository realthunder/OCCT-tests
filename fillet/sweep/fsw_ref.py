# fsw.py's cases, each made in pieces and again on the shape refined
# (removeSplitter), Part's check(True) run on both results. Run by drive.py
# with WORKER=fsw_ref.py (and TIMEOUT=400: two fillets and two checks a case).
# env: as fsw.py, plus NAME (the shape's name in shapes.lst) and SKIP, a
#      baseline file: the shape's cases refused there are not run ("skip").
# A result is <in pieces>|<refined>, each ok:<volume>:<max tol>:<c|b> (b:
# check(True) reports something), BAD:..., EXC or NULL; the refined one ends
# with :<edges found>/<edges asked> -- the edges are found again by their
# middles, and one that is gone was a split itself -- or is "noedge".
# refcmp.py classes the results.
import itertools, os, sys
import Part

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from loose_ends import loose, widest  # noqa: E402


def emit(s):
    os.write(1, ("\n" + s + "\n").encode())


mode = os.environ.get("MODE", "edge")
start = int(os.environ.get("START", "0"))
radii = [float(x) for x in os.environ.get("RADII", "0.3 0.8 2" if mode == "edge" else "0.3 1").split()]
name = os.environ["NAME"]
skip = set()
for l in open(os.environ["SKIP"]):
    w = l.split()
    if len(w) == 3 and w[0] == name and w[2] in ("EXC", "TIMEOUT", "CRASH"):
        skip.add(w[1])
s = Part.read(os.environ["SHAPE"])
brep = s.exportBrepToString()
edges = s.Edges
ref = s.removeSplitter()
rbrep = ref.exportBrepToString()
redges = ref.Edges
rmap = {}
inloose, rinloose = widest(s), widest(ref)  # a result may be as loose as its input


def refedge(i):
    if i not in rmap:
        e = edges[i - 1]
        m = Part.Vertex(e.valueAt((e.FirstParameter + e.LastParameter) / 2))
        c = [k for k, x in enumerate(redges) if x.distToShape(m)[0] < 1e-6]
        rmap[i] = c[0] if c else None
    return rmap[i]


def free(e):
    return not e.Degenerated and len(s.ancestorsOfType(e, Part.Face)) == 2


def stat(f, inloose):
    if f.isNull():
        return "NULL"
    tol = max([y.Tolerance for y in f.Edges] + [y.Tolerance for y in f.Vertexes])
    if not f.isValid():
        return "BAD:%.10g:%.3g:b" % (f.Volume, tol)
    try:
        f.check(True)
        b = "c"
    except Exception:
        b = "b"
    # LOOSE: valid, with an edge's curve short of its vertex (loose_ends.py)
    st = "LOOSE" if loose(f, inloose)[0] else "ok"
    return "%s:%.10g:%.3g:%s" % (st, f.Volume, tol, b)


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
    if key in skip:
        emit("%d %s skip" % (n, key))
        continue
    x = Part.Shape()
    x.importBrepFromString(brep, False)
    try:
        a = stat(x.makeFillet(r, [x.Edges[i - 1] for i in st]), inloose)
    except Exception:
        a = "EXC"
    red = []
    for i in st:
        k = refedge(i)
        if k is not None and k not in red:
            red.append(k)
    if not red:
        b = "noedge"
    else:
        y = Part.Shape()
        y.importBrepFromString(rbrep, False)
        try:
            b = stat(y.makeFillet(r, [y.Edges[k] for k in red]), rinloose)
        except Exception:
            b = "EXC"
        b += ":%d/%d" % (len(red), len(st))
    emit("%d %s %s|%s" % (n, key, a, b))
emit("DONE")
