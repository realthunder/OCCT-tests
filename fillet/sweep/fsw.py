# One shape's fillet sweep, run by drive.py inside FreeCADCmd.
# env: SHAPE (a brep), MODE (edge | vertex), START (the first case to run),
#      RADII (default "0.3 0.8 2" for edge, "0.3 1" for vertex),
#      OP (fillet, the default, or chamfer: makeChamfer at the same sizes).
# edge:   every edge between two faces, alone, at each radius.
# vertex: at every vertex of 3+ such edges, all of them, every pair and each
#         alone, at each radius.
# Prints "N <count>", then per case "T <index> <case>" before it runs and
# "<index> <case> <result>" after, then "DONE".
# A case is E<edge>@<r> or V<vertex>:<edge>,<edge>,...@<r>. A result is
# ok:<volume>:<max tol>:<faces>, BAD:... (made but not valid), LOOSE:...:<gap>
# (valid, but an edge's curve ends farther from its vertex than ten times the
# edge's tolerance, 1e-4 and any gap of the input's own: BRepCheck lets the
# vertex's tolerance cover it),
# EXC or NULL.
# Every case fillets a fresh copy of the input: a fillet that succeeds raises
# the tolerances of the sub-shapes it shares with its input, and one that
# fails can leave it changed, so reusing one input makes a result depend on
# the cases before it.
import itertools, os, sys
import Part

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from loose_ends import loose, widest  # noqa: E402


def emit(s):
    os.write(1, ("\n" + s + "\n").encode())


mode = os.environ.get("MODE", "edge")
chamfer = os.environ.get("OP", "fillet") == "chamfer"
start = int(os.environ.get("START", "0"))
radii = [float(x) for x in os.environ.get("RADII", "0.3 0.8 2" if mode == "edge" else "0.3 1").split()]
s = Part.read(os.environ["SHAPE"])
brep = s.exportBrepToString()
inloose = widest(s)  # a result may be as loose as its input
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
    x = Part.Shape()
    x.importBrepFromString(brep, False)
    try:
        f = (x.makeChamfer if chamfer else x.makeFillet)(r, [x.Edges[i - 1] for i in st])
        if f.isNull():
            res = "NULL"
        else:
            tol = max([y.Tolerance for y in f.Edges] + [y.Tolerance for y in f.Vertexes])
            gap = loose(f, inloose)[0] if f.isValid() else 0.0
            res = "%s:%.10g:%.3g:%d" % ("BAD" if not f.isValid() else "LOOSE" if gap else "ok",
                                        f.Volume, tol, len(f.Faces))
            if gap:
                res += ":%.3g" % gap
    except Exception:
        res = "EXC"
    emit("%d %s %s" % (n, key, res))
emit("DONE")
