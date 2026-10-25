# Regression tests for the fork's fillet (TKFillet / ChFi3d) fixes.
#
# Run with any FreeCAD build linked against this OCCT:
#
#     FreeCADCmd tests/fork/fillet/run_tests.py
#
# Exit code is 0 when no expected-pass case fails.  Known-broken cases are
# declared XFAIL below; when one starts passing the suite prints
# UNEXPECTED-PASS so its expectation (and README.md) can be updated.
#
# See README.md for what each case covers and the history of each problem.

import math
import os
import sys
import traceback

import FreeCAD as App
import Part

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(HERE, "models")
sys.path.insert(0, os.path.dirname(HERE))
from loose_ends import loose, widest  # noqa: E402
from flat_end import FlatEnd  # noqa: E402
RELTOL = 1e-4


def emit(line):
    # FreeCAD redirects sys.stdout into its own console, which swallows
    # script output under FreeCADCmd - write straight to fd 1.
    os.write(1, (line + "\n").encode())


# Every case here pins what the fork does. On another OCCT -- upstream's, as
# FreeCAD can load it -- they fail for want of the fork, so the suite says so
# and runs nothing. The fork is found as FreeCAD finds it, by a C function of
# its TKBRep; a FreeCAD from before Part.hasOCCTFunction runs the suite.
if hasattr(Part, "hasOCCTFunction") and not Part.hasOCCTFunction("TKBRep", "SetFuncShowTopoShape"):
    emit("SKIP: not the OCCT fork (TKBRep has no SetFuncShowTopoShape)")
    emit("summary: SKIP=1")
    sys.stdout.flush()
    os._exit(0)


# FreeCAD freezes shape values when it finds this fork, and a frozen input is
# protected from an algorithm that edits it. Run unfrozen by default, as any
# other build of FreeCAD runs, so such an edit shows (FILLET_FREEZE=1 for the
# frozen path).
App.ParamGet("User parameter:BaseApp/Preferences/Mod/Part").SetBool(
    "ImmutableShapeValues", os.environ.get("FILLET_FREEZE", "0") != "0")


def signature(shape):
    """What a fillet must leave of its input: the shape valid, the volume."""
    return (shape.isValid(), round(shape.Volume, 6))


def ends_problem(shape, allowed=0.0):
    """'loose end ...' when an edge's curve ends past its vertex by more than
    <allowed> too (see ../loose_ends.py: BRepCheck lets the vertex's
    tolerance cover the gap)."""
    gap, i = loose(shape, allowed)
    return "loose end %.3g at Edge%d" % (gap, i) if gap else None


results = []  # (name, verdict, detail); verdict in PASS/FAIL/XFAIL/UNEXPECTED-PASS


def report(name, ok, expect_fail, detail):
    if ok and not expect_fail:
        verdict = "PASS"
    elif ok and expect_fail:
        verdict = "UNEXPECTED-PASS"
    elif not ok and expect_fail:
        verdict = "XFAIL"
    else:
        verdict = "FAIL"
    results.append((name, verdict, detail))
    emit("%-32s %-16s %s" % (name, verdict, detail))


def edge_between(shape, a, b):
    """The 1-based index of the edge of `shape` whose ends are `a` and `b`."""
    want = sorted([tuple(round(c, 6) for c in a), tuple(round(c, 6) for c in b)])
    for i, e in enumerate(shape.Edges, 1):
        if sorted(tuple(round(c, 6) for c in v.Point) for v in e.Vertexes) == want:
            return i
    raise ValueError("no edge between %s and %s" % (a, b))


# ---------------------------------------------------------------------------
# Document cases: recompute the captured model, everything must stay valid.
# ---------------------------------------------------------------------------

def document_case(name, filename, volumes=None):
    """Open models/<filename>, force a full recompute and require every
    feature to recompute without error into a valid shape.  `volumes` maps
    object Name -> expected volume of its shape."""
    try:
        doc = App.openDocument(os.path.join(MODELS, filename))
        try:
            for obj in doc.Objects:
                obj.touch()
            doc.recompute()
            bad = []
            for o in doc.Objects:
                states = [str(s) for s in o.State]
                if "Invalid" in states or "Error" in states:
                    bad.append("%s:%s" % (o.Name, states))
                # the property only: getattr() falls back to Part.getShape()
                if "Shape" not in o.PropertiesList:
                    continue
                s = o.getPropertyByName("Shape")
                if hasattr(s, "isValid") and not s.isNull() and not s.isValid():
                    bad.append("%s:invalid-shape" % o.Name)
                elif hasattr(s, "isValid") and not s.isNull() and loose(s)[0]:
                    bad.append("%s:loose-end %.3g" % (o.Name, loose(s)[0]))
            if not bad and volumes:
                for oname, vol in volumes.items():
                    got = doc.getObject(oname).Shape.Volume
                    if abs(got - vol) > RELTOL * abs(vol):
                        bad.append("%s:volume %.4f != %.4f" % (oname, got, vol))
            report(name, not bad, False, "; ".join(bad) if bad else "ok")
        finally:
            App.closeDocument(doc.Name)
    except Exception:
        report(name, False, False, traceback.format_exc().splitlines()[-1])


# ---------------------------------------------------------------------------
# Shape cases: one fillet on a stored or built shape.
# ---------------------------------------------------------------------------

def fillet_case(name, shape, edge_index, radius, expect, ref_volume=None, max_tol=None,
                chamfer=False, vol_tol=None, bop=False, flat=False, within=False):
    """makeFillet(radius, [Edge<edge_index>]); edge_index may be a list;
    makeChamfer(radius, ...) with chamfer=True, radius a pair for two
    distances. flat=True: with the flat end at a vertex (../flat_end.py).

    expect='pass':  a valid solid, one closed shell, the input left as it was,
                    ref_volume when given (within vol_tol when given, else
                    RELTOL of it), and no edge or vertex tolerance above
                    max_tol when given; with bop=True, nothing BOP's argument
                    check (Shape.check(True)) reports; with within=True, the
                    result's tessellation inside the input's bounding box (a
                    fillet takes material away, or fills a concave corner:
                    nothing it makes lies outside -- a spike does, at a
                    volume a spike hardly changes).
    expect='xfail': known broken (see README.md); an exception, an invalid
                    shape, a loose end or an open shell counts as the
                    expected failure.
    Every result made is checked for loose ends: an edge whose curve ends
    past its vertex (../loose_ends.py), which BRepCheck lets pass -- by
    more than the input's own gap, and than max_tol when given, the
    looseness the case accepts.
    """
    try:
        before = signature(shape)
        indices = edge_index if isinstance(edge_index, list) else [edge_index]
        op = shape.makeChamfer if chamfer else shape.makeFillet
        sizes = radius if isinstance(radius, tuple) else (radius,)
        with FlatEnd(flat):
            r = op(*sizes, [shape.Edges[i - 1] for i in indices])
        problems = []
        if signature(shape) != before:
            problems.append("input changed: valid=%s vol=%.4f" % signature(shape))
        if not r.isValid():
            problems.append("invalid")
        else:
            problems += [p for p in [ends_problem(r, max(max_tol or 0.0, widest(shape)))]
                         if p]
        if len(r.Shells) != 1:
            problems.append("shells=%d" % len(r.Shells))
        elif not r.Shells[0].isClosed():
            problems.append("open-shell")
        if not problems and ref_volume is not None:
            if abs(r.Volume - ref_volume) > (vol_tol if vol_tol is not None
                                             else RELTOL * abs(ref_volume)):
                problems.append("volume %.4f != %.4f" % (r.Volume, ref_volume))
        if not problems and max_tol is not None:
            tol = max([e.Tolerance for e in r.Edges] + [v.Tolerance for v in r.Vertexes])
            if tol > max_tol:
                problems.append("tolerance %.3g > %.3g" % (tol, max_tol))
        if not problems and bop:
            try:
                r.check(True)
            except Exception as e:
                problems.append("bop: " + " ".join(str(e).split())[:80])
        if not problems and within:
            box = shape.BoundBox
            box.enlarge(1e-3)
            out = [p for f in r.Faces for p in f.tessellate(0.05)[0] if not box.isInside(p)]
            if out:
                far = max(out, key=lambda p: box.Center.distanceToPoint(p))
                problems.append("%d points outside the input's box, one at (%.3f, %.3f, %.3f)"
                                % (len(out), far.x, far.y, far.z))
        ok = not problems
        detail = "; ".join(problems) if problems else "vol=%.4f" % r.Volume
    except Exception as e:
        ok = False
        detail = "EXCEPTION " + str(e).strip().splitlines()[-1]
    report(name, ok, expect == "xfail", detail)


def exact_case(name, shape, edge_index, radius, kind):
    """makeFillet(radius, [Edge<edge_index>]) is valid and makes no B-spline
    face: the fillet is the exact surface -- `kind` faces more than the input
    has, and as many B-spline faces as it."""
    try:
        def count(s, k):
            return sum(1 for f in s.Faces if f.Surface.__class__.__name__ == k)
        r = shape.makeFillet(radius, [shape.Edges[edge_index - 1]])
        problems = []
        if not r.isValid():
            problems.append("invalid")
        else:
            problems += [p for p in [ends_problem(r, widest(shape))] if p]
        if count(r, "BSplineSurface") != count(shape, "BSplineSurface"):
            problems.append("%d B-spline faces for %d" % (count(r, "BSplineSurface"),
                                                          count(shape, "BSplineSurface")))
        if count(r, kind) <= count(shape, kind):
            problems.append("no %s face more" % kind)
        ok = not problems
        detail = "; ".join(problems) if problems else "vol=%.4f" % r.Volume
    except Exception as e:
        ok = False
        detail = "EXCEPTION " + str(e).strip().splitlines()[-1]
    report(name, ok, False, detail)


def nocrash_case(name, shape, edge_index, radius):
    """The fillet may fail, but must not take the process down; the input
    must be left as it was either way. A crash ends the run: the missing
    summary line is the failure."""
    before = signature(shape)
    edges = [shape.Edges[edge_index - 1]]
    try:
        r = shape.makeFillet(radius, edges)
        detail = "valid=%s vol=%.4f" % (r.isValid(), r.Volume)
    except Exception as e:
        detail = "refused: " + str(e).strip().splitlines()[-1]
    ok = signature(shape) == before
    report(name, ok, False, detail if ok else "input changed; " + detail)


def sound_case(name, shape, edge_index, radius, expect="pass", chamfer=False):
    """The fillet (the chamfer with chamfer=True) may be refused, but a shape
    it makes must be a valid solid with one closed shell; the input must be
    left as it was either way."""
    before = signature(shape)
    # the edges looked up outside the try: a wrong index is the case's fault,
    # not a refusal
    indices = edge_index if isinstance(edge_index, list) else [edge_index]
    edges = [shape.Edges[i - 1] for i in indices]
    op = shape.makeChamfer if chamfer else shape.makeFillet
    try:
        r = op(radius, edges)
        ok = r.isValid() and len(r.Shells) == 1 and r.Shells[0].isClosed()
        detail = "vol=%.4f" % r.Volume if ok else "invalid result, vol=%.4g" % r.Volume
        loose_end = ends_problem(r, widest(shape)) if ok else None
        if loose_end:
            ok, detail = False, loose_end
    except Part.OCCError as e:
        ok = True
        detail = "refused: " + str(e).strip().splitlines()[-1]
    if signature(shape) != before:
        ok = False
        detail = "input changed; " + detail
    report(name, ok, expect == "xfail", detail)


# realthunder/FreeCAD#523: a 10 box with a three-quarter cylinder (r 2) at its
# corner on the z axis, made by Part's Connect. The cylinder's seam -- the
# line x=2, y=0 where it meets the box's side -- stayed an edge with both
# pcurves on the cylinder, and a fillet on the box edge ending there read
# the pcurve a period away from the face.
document_case("issue523_document", "issue523_fillet_explodes.FCStd",
              {"Fillet": 1092.5263})

bc = Part.read(os.path.join(MODELS, "issue523_box_cylinder.brep"))
top = edge_between(bc, (2, 0, 10), (10, 0, 10))     # ends on the seam, at the top
bottom = edge_between(bc, (2, 0, 0), (10, 0, 0))    # the same at the bottom
mtop = edge_between(bc, (0, 2, 10), (0, 10, 10))    # its mirror image: no seam
mbottom = edge_between(bc, (0, 2, 0), (0, 10, 0))
arc_top = edge_between(bc, (0, 2, 10), (2, 0, 10))  # the cylinder's top arc
arc_bottom = edge_between(bc, (0, 2, 0), (2, 0, 0))

# The fillets on the edges ending on the seam match their mirror images.
for r, vol in ((0.5, 1093.8183), (1.0, 1092.5263)):
    fillet_case("seam_end_top_r%g" % r, bc, top, r, "pass", vol)
    fillet_case("seam_end_bottom_r%g" % r, bc, bottom, r, "pass", vol)
    fillet_case("mirror_top_r%g" % r, bc, mtop, r, "pass", vol)
    fillet_case("mirror_bottom_r%g" % r, bc, mbottom, r, "pass", vol)
# At the cylinder's radius the fillet's end reaches the far end of the
# cylinder's face as well: the fillet's line on the top (bottom) is tangent
# to the cylinder there, at the line's very end. The mirror cases found
# that point a rounding error past the line's end and refused the corner.
# The corner's curve on the cylinder leaves the face's circle at fourth
# order, and its approximation ran a rounding error past it: on the bottoms
# BRepCheck saw the wire cross itself. The curve is now kept on the face,
# leaving the circle at an angle (README.md). What is left of the top
# (bottom) is the box's rectangle and the cylinder's disc, touching at that
# vertex: two faces sharing it, which BOP's check passes (one face through
# two vertices there 4e-15 apart, before).
fillet_case("seam_end_top_r2", bc, top, 2.0, "pass", 1087.3009, bop=True)
fillet_case("seam_end_bottom_r2", bc, bottom, 2.0, "pass", 1087.3009, bop=True)
fillet_case("mirror_top_r2", bc, mtop, 2.0, "pass", 1087.3009, bop=True)
fillet_case("mirror_bottom_r2", bc, mbottom, 2.0, "pass", 1087.3009, bop=True)
# The same as the picture of the split top (pictures/cases.py).
fillet_case("pinch_top_r2", bc, top, 2.0, "pass", 1087.3009, bop=True)
# Past the cylinder's radius the fillet's line on the top misses the
# cylinder; the end has to be cut by the cylinder carried into the box for
# y < 2 and by the box's side x = 0 beyond, and the top splits in two. That
# end is still refused; the fillet is made by the corner setback fallback
# (fcad docs/CornerBlending.md section 9), which cuts the fillet back from
# the corner and closes it with one patch, at both radii where the fillet
# meets the corner. At 3 that took twice the radius (1072.1768, the patch
# over most of the cylinder's top) until the patch was approximated to its
# boundary rather than to the plate: the nearer setbacks had left edges
# looser than a twentieth of the radius. Its curve on the box's side hooked
# back into the stripe until the end held at right angles to its chord was
# freed (1085.4352 at 2.5, 1082.0690 at 3 with the hook). The fillet run
# past the end would be the boolean's, the groove carried past the end,
# less the cylinder, cut from the shape: 1083.3063 at 2.5, 1078.3294 at 3.
for r, vol in ((2.5, 1087.9914), (3.0, 1086.0296)):
    fillet_case("seam_end_top_r%g" % r, bc, top, r, "pass", vol)
    fillet_case("mirror_top_r%g" % r, bc, mtop, r, "pass", vol)

# Every edge at radius 1: nothing else moved.
for i in range(1, len(bc.Edges) + 1):
    fillet_case("every_edge_r1_e%02d" % i, bc, i, 1.0, "pass")

# A fillet of the cylinder's own radius on its arcs: the fillet's line on the
# top face is a point. It crashed in IntersUpdateOnSame.
nocrash_case("arc_top_r2_no_crash", bc, arc_top, 2.0)
nocrash_case("arc_bottom_r2_no_crash", bc, arc_bottom, 2.0)

# realthunder/FreeCAD#962: a fillet whose end lies on a face split into
# coplanar pieces (a PartDesign body without Refine). A 10x10x14 block with a
# slot cut down to z=5 (y 3..6); the fillet is on the outer edge of the slot,
# x=10, y=3, which ends on the slot's floor.
V = App.Vector


def slotted(wall=False, outer=False):
    """The slotted block; `wall` splits the slot's wall (y=3) by a vertical
    edge 0.7 from the outer face, `outer` splits the outer face (x=10) by the
    spine's own line below the floor."""
    s = Part.makeBox(10, 10, 14).cut(Part.makeBox(12, 3, 10, V(-1, 3, 5)))
    for on, (a, b) in ((outer, (V(10, 3, 0), V(10, 3, 5))),
                       (wall, (V(9.3, 3, 5), V(9.3, 3, 20)))):
        if on:
            s = s.generalFuse([Part.LineSegment(a, b).toShape()])[0].Solids[0]
    return s


plain = slotted()
spine = edge_between(plain, (10, 3, 5), (10, 3, 14))
for r in (0.5, 0.8, 1.0, 2.0):
    ref = plain.makeFillet(r, [plain.Edges[spine - 1]]).Volume
    for tag, s in (("wall", slotted(wall=True)), ("outer", slotted(outer=True)),
                   ("both", slotted(wall=True, outer=True))):
        # wider than the wall's piece at the vertex from 0.7 on
        fillet_case("slot_split_%s_r%g" % (tag, r), s,
                    edge_between(s, (10, 3, 5), (10, 3, 14)), r, "pass", ref)

# The model's own shape: the Pocket002 the fillet is made on. Edges 101, 102,
# 104 and 105 are the outer edges of four slots like the block's, the wall's
# piece at the floor 0.692 and 0.787 wide; edge 50 ends where the wall
# (y=10.2) continues as another face above the end face, a chamfer.
p2 = Part.read(os.path.join(MODELS, "issue962_pocket002.brep"))
for name, a, b in (("e101", (50, 13.7, 22), (50, 13.7, 14)),
                   ("e102", (50, 17.1, 14), (50, 17.1, 22)),
                   ("e104", (50, 20.3, 22), (50, 20.3, 14)),
                   ("e105", (50, 23.7, 14), (50, 23.7, 22))):
    fillet_case("issue962_%s_r0.8" % name, p2, edge_between(p2, a, b), 0.8, "pass",
                11580.7739)
# (Edges 50 and 56 ended in a plate until 2026-10-13, at 11583.8075,
# 11581.7204 and 11581.7068 with tolerances to 0.05; the arm's top alone is
# cut since -- README.md, "A side stopped on a split in the plane of the
# face at end" -- and they take the quarter round of their 17.75.)
e50 = edge_between(p2, (38.5, 10.2, -3.75), (38.5, 10.2, 14))
fillet_case("issue962_e50_r0.3", p2, e50, 0.3, "pass", 11583.7984, 2e-4, vol_tol=1e-4, bop=True)
fillet_case("issue962_e50_r0.8", p2, e50, 0.8, "pass", 11581.7266, 2e-4, vol_tol=1e-4, bop=True)
# Edge 56, e50's mirror image across the block (y=27.2 for 10.2): its foot is
# the five-face corner at (38.5,27.2,-3.75), filled by a plate held tangent to
# the stripe, which missed its boundary by 0.09 and folded; the approximation
# strayed 0.48, the corner kept tolerances up to 1.18 and a face whose volume
# integrates to anything from 2.0 to 5.0 taken. Built again on positions
# alone it takes what e50 takes.
e56 = edge_between(p2, (38.5, 27.2, -3.75), (38.5, 27.2, 14))
fillet_case("issue962_e56_r0.8", p2, e56, 0.8, "pass", 11581.7266, 2e-4, vol_tol=1e-4, bop=True)
# Edge 33, the arm's top on its side, ending at the corner (38.5,10.2,-3.75)
# under e50. The plate's boundary on the block's side (y=10.2) is a projection
# that came out running from the corner's far end to its near one, and was
# stored as running the other way: its edge had its FORWARD vertex at its
# last parameter, which BRepCheck does not look at and GProp walks backwards
# (9.4 of volume taken at 0.3, where 0.55 is due), and the plate's outline
# had two curves head to head, which turned the plate face over.
e33 = edge_between(p2, (17.356038, -9.42499, -3.75), (38.5, 10.2, -3.75))
for r, vol in ((0.1, 11584.0782), (0.3, 11583.5858)):
    fillet_case("issue962_e33_r%g" % r, p2, e33, r, "pass", vol, 0.05)
# Edges 36 and 49, the foot of the block where the arm meets it (x=38.5,
# z -9.75..-3.75): each fine alone, together they gave an invalid solid 7225
# too large. The bottom is two coplanar faces, the arm's and the block's,
# split along x=38.5; one corner cut that seam, the other met its line past
# the seam's end, and both versions of the seam stayed.
e36 = edge_between(p2, (38.5, 27.2, -3.75), (38.5, 27.2, -9.75))
e49 = edge_between(p2, (38.5, 10.2, -3.75), (38.5, 10.2, -9.75))
fillet_case("issue962_e36_e49_r0.8", p2, [e36, e49], 0.8, "pass", 11584.2053)
# Edges 25 and 26 (and 33 and 34 above them), the arm's side's foot and the
# curved wall's (a cylinder of 19.75 about z), at the corner where the
# outline turns into the body by 18.6 deg: the corner's point on the wall's
# line, a circle the stripe is carried on 3.4 rad past the vertex, was taken
# a turn on -- the fillet's torus face a turn over itself, 21233 for 11583
# (README.md, "A corner's point a turn round a circle").
_v18 = (17.3560383244383, -9.42498985042571)
_v13 = (-13.6162035198476, -14.3059953063773)
for z, ea, eb, vols in ((-9.75, 25, 26, (11582.8865, 11570.2997)),
                        (-3.75, 33, 34, (11582.8839, 11570.2035))):
    pair = [edge_between(p2, _v18 + (z,), (38.5, 10.2, z)),
            edge_between(p2, _v13 + (z,), _v18 + (z,))]
    for r, vol in zip((0.3, 1), vols):
        fillet_case("issue962_arm_corner_e%d_e%d_r%g" % (ea, eb, r), p2, pair, r, "pass", vol,
                    1e-4, vol_tol=1e-4, bop=True)
# and the Fillet itself, all twelve edges
twelve = [edge_between(p2, a, b) for a, b in (
    ((50, 10.2, -3.75), (50, 10.2, 22)), ((50, 13.7, 22), (50, 13.7, 14)),
    ((50, 17.1, 14), (50, 17.1, 22)), ((50, 20.3, 22), (50, 20.3, 14)),
    ((50, 23.7, 14), (50, 23.7, 22)), ((50, 27.2, -3.75), (50, 27.2, 22)),
    ((38.5, 27.2, -3.75), (38.5, 27.2, 14)), ((38.5, 27.2, -3.75), (38.5, 27.2, -9.75)),
    ((38.5, 10.2, -3.75), (38.5, 10.2, 14)), ((38.5, 10.2, -3.75), (38.5, 10.2, -9.75)),
    ((10.898402, 16.470802, -3.75), (10.898402, 16.470802, -9.75)),
    ((17.356038, -9.42499, -3.75), (17.356038, -9.42499, -9.75)))]
fillet_case("issue962_fillet_r0.8", p2, twelve, 0.8, "pass", 11552.7705)

# The edge along the top of a rib (z=32.25, y=20.3, x 35.5..38.5), whose end
# face slopes down (normal 0.46,0,0.89); the rib's wall (y=20.3) is in two
# coplanar pieces, split at x=39.197 where the slope comes down to 31.886.
# From r=0.364 on, the fillet's line on the wall passes under the slope's
# edge with the wall's first piece, crosses the split and meets the slope on
# the second: the walk stopped at the spine's end with that side in the
# face, and the end was made by the plate of an intersection at end -- off
# by up to 0.017 (a chamfer 0.08) at r 0.4..0.7, invalid from 0.8. The line
# is now carried over the split. Volumes: the same fillet on the shape
# refined (removeSplitter), to 1e-5 since the chain's other end (below) is
# made too.
rib = edge_between(p2, (35.5, 20.3, 32.25), (38.5, 20.3, 32.25))
fillet_case("issue962_rib_top_r0.5", p2, rib, 0.5, "pass", 11582.884638, 1e-4, vol_tol=1e-5)
fillet_case("issue962_rib_top_r0.8", p2, rib, 0.8, "pass", 11580.921269, 1e-4, vol_tol=1e-5)
fillet_case("issue962_rib_top_r0.95", p2, rib, 0.95, "pass", 11579.597504, 1e-4, vol_tol=1e-5)
fillet_case("issue962_rib_top_chamfer_0.8", p2, rib, 0.8, "pass", 11576.625155, 1e-4,
            chamfer=True, vol_tol=1e-5)
# The outer ribs' tops (y=10.2 and 27.2) end at x=38.5 on the same slope,
# and there the block's side is split at x=38.5 exactly: the wall's piece
# ends with the edge, the fillet's line on it stops on the split (the slant
# block split at its slope's start, below). The chain runs from the arm's
# 45 deg underside up the rib's front to its top, its surfaces not one to
# an edge; there the split, a regular edge beside the fillet's end, sent the
# end to a plate, which failed: refused at every radius. Volumes: the
# refined shape's.
for name, y in (("e72", 10.2), ("e94", 27.2)):
    und = edge_between(p2, (38.5, y, 14), (35.470838, y, 17.029162))
    for r, vol in ((0.3, 11583.691087), (0.8, 11580.970356), (2.0, 11564.542048)):
        fillet_case("issue962_%s_r%g" % (name, r), p2, und, r, "pass", vol, 2e-4, vol_tol=1e-4,
                    bop=True)

# The inner slots' floors (z=14) against the block's side (x=38.5), edges 52
# and 54: at either end stands a rib's wall, in two pieces, the one at the
# floor's corner 0.4606 wide (0.6973 on edge 54), and the corner has four
# edges -- the spine, the block's side going on under the rib's 45 deg
# underside in line with it, the underside's edge with the wall and the
# wall's with the floor. The fillet's line on the side runs on in its face
# to the far edge, the one on the floor ends on the wall's far piece: neither
# on an edge of the vertex, and the loop over the faces at such an end found
# no way round: refused from the piece's width on. Volumes: the refined
# shape's; a hair over the width (0.4625, 0.4635) the cut crosses the split's
# line within 1e-5 of its foot.
for name, y, radii in (("e52", 13.7, ((0.4625, 11583.983843), (0.4635, 11583.983168),
                                    (0.465, 11583.982151), (0.8, 11583.672945),
                                    (2.0, 11581.221334))),
                       ("e54", 20.3, ((0.8, 11583.672945), (2.0, 11581.221334)))):
    flo = edge_between(p2, (38.5, y, 14), (38.5, y + 3.4, 14))
    for r, vol in radii:
        fillet_case("issue962_%s_r%g" % (name, r), p2, flo, r, "pass", vol, 2e-4, vol_tol=1e-5,
                    bop=True)

# The same chain's other end: from the top it runs down the rib's front,
# tangent, and its last edge -- the rib's wall (y=20.3) against the 45 deg
# underside of its overhang -- ends at the rib's foot (38.5,20.3,14) on the
# block's top (z=14), four edges there. The wall's line comes down to the
# block's top at x=38.5+1.414r, past the split at x=39.197 from r=0.493 on,
# and from r=0.986 the walk itself crosses the split before the end. The
# end was made off by up to 0.09 at r 0.5..0.98 (all "valid": the exact
# fillet's line was cut at the split, and the walk past the end stopped
# there), and failed from 0.99 (the line's end on the block's top edge
# beyond the split, an edge without the corner's vertex, was taken for a
# cap). Volumes: the refined shape's, to 1e-5.
for r, vol in ((0.6, 11582.331352), (0.8, 11580.921269), (1.0, 11579.105436),
               (1.5, 11572.726674), (2.5, 11552.242546)):
    fillet_case("issue962_rib_foot_r%g" % r, p2, rib, r, "pass", vol, 2e-4, vol_tol=1e-5)
# Where the wall's line at the spine's end lies within 1e-3 of the split
# (r = 0.98571): the crossing was looked for only from 2e-3 past the line's
# end, and below the coincidence the end was made off by 0.09 (0.9852 to
# 0.9858) or invalid (0.986). Just above it the exact fillet's line is cut
# at the split 1e-3 or less inside the edge, and the walk from there failed
# (0.9862, 0.9863) or stopped at the underside's edge (0.9865 to 0.9868,
# invalid); the line now runs on over the split (README.md).
for r, vol in ((0.9855, 11579.250754), (0.986, 11579.245778), (0.9862, 11579.243788),
               (0.9865, 11579.240801), (0.9868, 11579.237813)):
    fillet_case("issue962_rib_foot_r%g" % r, p2, rib, r, "pass", vol, 2e-4, vol_tol=1e-5)
# A chamfer on the chain from 1 on: the chain turns from the rib's top down
# its front on an arc of radius 1, and the chamfer's line on the wall turns
# back on itself there -- a self-intersecting wire, on the refined shape as
# well (1 is refused on both). Refused before, at the foot; invalid now.
fillet_case("issue962_rib_chamfer_1.2", p2, rib, 1.2, "xfail", chamfer=True)

# The arm's top (z=-3.75) against the block's wall x=38.5, and the top's
# edge with the arm's slanting side (e33 above): both end at
# (38.5,10.2,-3.75), five edges there -- the block's side (y=10.2) and the
# arm's foot below the top are one plane in two faces, split along the top's
# level, and the edges on either side of the two, the wall's and the
# slanting side's, are one line. On the shape refined that is a corner of
# four edges, two of them in line, where the fillet cuts only the face that
# is not between the two. In pieces each face was cut for itself: the
# fillet's section in the pieces' plane came out twice, there and back, and
# the lower piece's wire crossed itself (0.8, and 2 on the slanting side),
# or the end failed and the corner setback fallback made it, tolerances to
# 0.12 (0.3, 2). The other end of the wall's edge, at y=27.2, is the same.
# Volumes: the refined shape's (on the slanting side this shape's own: the
# two results cut from each other leave nothing, while their volumes read
# 3e-3 apart at r=2, an ellipse and a circle's arc at the far end
# integrated differently).
ewall = edge_between(p2, (38.5, 10.2, -3.75), (38.5, 27.2, -3.75))
for r, vol in ((0.3, 11584.468959), (0.8, 11586.488030), (2.0, 11598.939732)):
    fillet_case("issue962_top_wall_r%g" % r, p2, ewall, r, "pass", vol, 1e-4, vol_tol=1e-5,
                bop=True)
for r, vol in ((0.8, 11580.223860), (2.0, 11559.992535)):
    fillet_case("issue962_top_slant_r%g" % r, p2, e33, r, "pass", vol, 1e-4, vol_tol=1e-5,
                bop=True)
for r, vol in ((0.8, 11589.625952), (2.0, 11618.859178)):
    fillet_case("issue962_top_wall_chamfer_%g" % r, p2, ewall, r, "pass", vol, 1e-4,
                chamfer=True, vol_tol=1e-5, bop=True)

# The mouth of the hexagonal pocket in the block's side (y=10.2), its edge
# at x=38.8, 0.3 from the split of that side at x=38.5 (the block's piece
# and the rib's above it, one plane). From r=0.3 the fillet's line on the
# side lies on the rib's piece, and the edge that closes the fillet's end --
# the pocket's next wall carried on from the corner to the line -- starts
# in the block's piece and crosses the split. It was put on the rib's piece
# whole, which left that face an open wire and the block's piece without
# its end: invalid from 0.301 to 1.2. At 0.3 the line runs along the split
# itself, and the walk did not start: the split was not taken for one on
# faces REVERSED in the shell (the miniature below has more of that
# coincidence). Volumes: the refined shape's.
ehex = edge_between(p2, (38.8, 10.2, 24.4248711), (38.8, 10.2, 19.5751289))
for r, vol in ((0.3, 11584.047745), (0.5, 11583.886647), (0.8, 11583.502170),
               (1.2, 11582.736864)):
    fillet_case("issue962_hex_mouth_r%g" % r, p2, ehex, r, "pass", vol, 2e-4, vol_tol=1e-5,
                bop=True)


def slant_block(mirror=False, at=5.0):
    """A 12x3 prism (y 0..3) whose top is flat (z=10) for x 0..4 and slopes
    down to z=6 at x=12; its front wall (y=0) split by a vertical edge at
    x=`at` (5, where the slope is at z=9.5 -- the rib above in miniature)."""
    prof = Part.Face(Part.makePolygon([V(0, 0, 0), V(12, 0, 0), V(12, 0, 6), V(4, 0, 10),
                                       V(0, 0, 10), V(0, 0, 0)]))
    s = prof.extrude(V(0, 3, 0))
    cut = Part.LineSegment(V(at, 0, 0), V(at, 0, 10 - (at - 4) / 2.0)).toShape()
    s = s.generalFuse([cut])[0].Solids[0]
    return s.mirror(V(0, 0, 0), V(1, 0, 0)) if mirror else s


# The fillet on the front top edge (y=0, z=10) at r > 0.5: its line on the
# wall (z=10-r) crosses the split before it meets the slope, at x=4+2r. The
# slope cuts the fillet off: the material taken is the fillet's cross-section
# (1-pi/4)r^2 swept from x=0 to the slope, (1-pi/4)r^2 (4 + 2cr), c the
# cross-section's centroid from the corner over r, (10-3pi)/(3(4-pi)).
# Tolerances as on the prism in one piece: the slope's cut, an ellipse
# approximated, ends at 1.5e-4 at r=2 there too.
csb = (10 - 3 * math.pi) / (3 * (4 - math.pi))
for tag, mirror in (("", False), ("_mirror", True)):
    sb = slant_block(mirror)
    sbe = edge_between(sb, (0, 0, 10), (-4 if mirror else 4, 0, 10))
    for r in (0.8, 1.5, 2.0):
        fillet_case("slant_split_wall%s_r%g" % (tag, r), sb, sbe, r, "pass",
                    312 - (1 - math.pi / 4) * r * r * (4 + 2 * csb * r), 2e-4)
    # The wall split at x=4, where the top's edge ends and the slope starts:
    # the wall's piece under the edge ends with it, and the fillet's line on
    # it stops on the split, an edge of the corner's vertex. The line is
    # carried over the split as one that stopped in its face before it (see
    # issue962_e72 below, where that end was refused: here, one fillet on
    # one edge, the loop over the faces at the end made it before, and the
    # result is the same). The same volumes; a chamfer takes
    # r^2/2 (4 + 2r/3).
    sbe = edge_between(slant_block(mirror, 4.0), (0, 0, 10), (-4 if mirror else 4, 0, 10))
    for r in (0.3, 0.8, 2.0):
        fillet_case("slant_split_at_slope%s_r%g" % (tag, r), slant_block(mirror, 4.0), sbe, r,
                    "pass", 312 - (1 - math.pi / 4) * r * r * (4 + 2 * csb * r), 2e-4,
                    vol_tol=1e-4, bop=True)
    fillet_case("slant_split_at_slope_chamfer%s_0.8" % tag, slant_block(mirror, 4.0), sbe, 0.8,
                "pass", 312 - 0.32 * (4 + 1.6 / 3), 2e-4, chamfer=True, vol_tol=1e-4, bop=True)


def rib_foot(mirror=False):
    """#962's rib foot in miniature: a block (x 0..10, y 0..6, z -4..0) and
    on it a rib (y 0..3, up to z=8) whose underside slopes at 45 deg from
    the block's edge (0,0) out to x=-3, z=3; the rib's front wall (y=3)
    split by a vertical edge at x=1."""
    blk = Part.makeBox(10, 6, 4, V(0, 0, -4))
    prof = Part.Face(Part.makePolygon([V(0, 0, 0), V(10, 0, 0), V(10, 0, 8), V(-3, 0, 8),
                                       V(-3, 0, 3), V(0, 0, 0)]))
    s = blk.fuse(prof.extrude(V(0, 3, 0))).removeSplitter()
    s = s.generalFuse([Part.LineSegment(V(1, 3, 0), V(1, 3, 8)).toShape()])[0].Solids[0]
    return s.mirror(V(0, 0, 0), V(1, 0, 0)) if mirror else s


# The fillet on the wall's edge with the underside, (0,3,0)..(-3,3,3): at
# the foot it ends at four edges, its line on the wall reaching the block's
# top at x=1.414r, past the split from r=0.71 (the walk crossing it before
# the end from r=1.41). The slope cuts the fillet off at x=-3, the block's
# top at z=0, both planes: the material taken is the cross-section swept
# between them through its centroid, (1-pi/4)r^2 (3sqrt2 + 2cr), c as for
# the slant block. 0.8 and 1.2 were off by 0.05 and 0.17, 1.5 and 2 failed.
# From 2.25 the line needs the walk past the vertex by more than half the
# edge (4.24), all the spine is extended by: refused, until the computation
# tried again with it extended 1.5 radius (ComputeLongExtension).
for tag, mirror in (("", False), ("_mirror", True)):
    rf = rib_foot(mirror)
    rfe = edge_between(rf, (0, 3, 0), (3 if mirror else -3, 3, 3))
    for r in (0.8, 1.2, 1.5, 2.0, 2.3, 2.5, 2.8):
        fillet_case("rib_foot_split%s_r%g" % (tag, r), rf, rfe, r, "pass",
                    538.5 - (1 - math.pi / 4) * r * r * (3 * math.sqrt(2) + 2 * csb * r),
                    2e-4, vol_tol=1e-4)


def ledge(mirror=False):
    """#962's arm and block in miniature: a base (z -4..0) whose outline
    runs (0,0) to (6,3) and on along y=3 to x=10, and on it a block (x 6..10,
    y 3..10, up to z=5). The block's side y=3 and the base's below it are one
    plane in two faces; at (6,3,0) the base's top meets the block's wall
    (x=6), the base's slanting side and those two, five edges."""
    base = Part.Face(Part.makePolygon([V(0, 10, -4), V(0, 0, -4), V(6, 3, -4), V(10, 3, -4),
                                       V(10, 10, -4), V(0, 10, -4)])).extrude(V(0, 0, 4))
    s = base.fuse(Part.makeBox(4, 7, 5, V(6, 3, 0)))
    return s.mirror(V(0, 0, 0), V(1, 0, 0)) if mirror else s


# The fillet between the base's top and the wall (concave) runs on past the
# wall's end at y=3 to the slanting side, which cuts it off: the material
# added is the cross-section (1-pi/4)r^2 over the edge's 7 and, past its
# end, over half the cross-section's centroid distance from the wall, c r
# (the side slopes 1 in 2). A chamfer's cross-section is r^2/2, its centroid
# r/3 from the wall. The fillet on the top's edge with the slanting side
# (convex) is cut by the wall's plane x=6 and the base's side x=0, parallel:
# what it takes is the cross-section over the edge's length sqrt(45). Before:
# as on #962 above -- 0.3 and 0.8 on the wall made by the fallback, off by
# 2e-4 and 5e-3, the rest invalid.
for tag, mirror in (("", False), ("_mirror", True)):
    lg = ledge(mirror)
    sg = -1 if mirror else 1
    lw = edge_between(lg, (sg * 6, 3, 0), (sg * 6, 10, 0))
    ls = edge_between(lg, (0, 0, 0), (sg * 6, 3, 0))
    # a shape of its own for each case: a fillet made raises the tolerances
    # of what its result shares with the input
    for r in (0.3, 0.8, 2.0):
        fillet_case("ledge_wall%s_r%g" % (tag, r), ledge(mirror), lw, r, "pass",
                    456 + (1 - math.pi / 4) * r * r * (7 + csb * r / 2), 1e-4, vol_tol=1e-5,
                    bop=True)
        fillet_case("ledge_slant%s_r%g" % (tag, r), ledge(mirror), ls, r, "pass",
                    456 - (1 - math.pi / 4) * r * r * math.sqrt(45), 1e-4, vol_tol=1e-5,
                    bop=True)
    for r in (0.5, 1.0):
        fillet_case("ledge_wall_chamfer%s_%g" % (tag, r), ledge(mirror), lw, r, "pass",
                    456 + 0.5 * r * r * (7 + r / 6), 1e-4, chamfer=True, vol_tol=1e-5,
                    bop=True)


def strip_box(mirror=False, ends=True):
    """A 10x10x4 box whose bottom (z=0) is split along x=2, 2 from its edge
    with the side x=0; with ends, the two end faces (y=0, y=10) are split
    along x=2 as well."""
    cuts = [Part.LineSegment(V(2, 0, 0), V(2, 10, 0)).toShape()]
    if ends:
        cuts += [Part.LineSegment(V(2, 0, 0), V(2, 0, 4)).toShape(),
                 Part.LineSegment(V(2, 10, 0), V(2, 10, 4)).toShape()]
    s = Part.makeBox(10, 10, 4).generalFuse(cuts)[0].Solids[0]
    return s.mirror(V(0, 0, 0), V(1, 0, 0)) if mirror else s


# The fillet on the bottom's edge with the side, at the width of the bottom's
# piece (2) and up to 1e-4 over it: its line on the bottom runs along the
# split, the piece goes under the fillet whole, and the line ends on the
# split's end vertices. It takes the cross-section over the edge's 10.
# With the end faces in one piece each: refused at 2 and 2.00005 on the box
# as built -- the split was not taken for one on faces REVERSED in the shell
# -- and made on its mirror image. With the end faces split too, the walk,
# on the far piece, ended on that piece's own edge at the vertex, not an
# edge of the corner: refused, or invalid with 12 of volume too much (2.0001);
# now the corner is that of the near pieces, the edge between them under
# the fillet. Further out the line lies on the far piece, and with the ends
# split the cut of the corner crosses their split: refused, until the corner
# took a cut over the end face's two pieces (below). A shape of its own for
# each case.
for ends, etag in ((True, ""), (False, "_plain_ends")):
    for tag, mirror in (("", False), ("_mirror", True)):
        se = edge_between(strip_box(mirror, ends), (0, 0, 0), (0, 10, 0))
        for r in (2.0, 2.00005, 2.0001):
            fillet_case("strip_box%s%s_r%g" % (etag, tag, r), strip_box(mirror, ends), se, r,
                        "pass", 400 - (1 - math.pi / 4) * r * r * 10, 1e-3, vol_tol=1e-5,
                        bop=True)
        fillet_case("strip_box%s%s_chamfer_2" % (etag, tag), strip_box(mirror, ends), se, 2.0,
                    "pass", 380.0, 1e-3, chamfer=True, vol_tol=1e-5, bop=True)
        # further out, the cut of the corner over the end face's two pieces
        # (below)
        for r in ((2.0002, 2.001, 2.005, 2.5, 3.9) if ends else (2.001, 2.5)):
            fillet_case("strip_box%s%s_r%g" % (etag, tag, r), strip_box(mirror, ends), se, r,
                        "pass", 400 - (1 - math.pi / 4) * r * r * 10, 1e-4, vol_tol=1e-5,
                        bop=True)

# #309's shape is all of that: its bottom, its side and its end faces in
# strips 2 wide. Edge 17 (x=2, z=-2, y -50..50) at 2: refused before; the
# refined shape's volume.
p309 = Part.read(os.path.join(HERE, "..", "draft", "models", "issue309_shape.brep"))
e309 = edge_between(p309, (2, 50, -2), (2, -50, -2))
fillet_case("issue309_e17_r2", p309, e309, 2.0, "pass", 12677.526391, 1e-3, vol_tol=1e-5,
            bop=True)


# The face at the fillet's end kept in two coplanar pieces, the one at the
# vertex narrower than the fillet: one side of the fillet ends on an edge of
# the far piece, past the vertex where the split between the two starts, and
# the cut of the corner runs over both pieces.
#
# At a corner of three edges alike (the strip box above, convex; a blind
# pocket's floor against its wall, concave) both sides end on edges, and the
# corner wanted them on one face. The cut crosses the split itself, which is
# cut there; the edge of the near piece from the split's foot to the corner
# is under the fillet. The strip box was refused. The pocket was made, by the
# loop over the faces at an end of several (PerformIntersectionAtEnd), which
# takes an arc past a split's foot; it is the corner's own cut now, to the
# same result.
def blind_pocket(mirror=False):
    """A 10x10x10 block with a blind pocket (x, y 2..8) from z=4 up, whose
    wall y=2 is split by a vertical edge at x=2.7, 0.7 from the wall x=2."""
    s = Part.makeBox(10, 10, 10).cut(Part.makeBox(6, 6, 6, V(2, 2, 4)))
    s = s.generalFuse([Part.LineSegment(V(2.7, 2, 4), V(2.7, 2, 10)).toShape()])[0].Solids[0]
    return s.mirror(V(0, 0, 0), V(1, 0, 0)) if mirror else s


# The floor's edge with the wall x=2: the fillet adds its cross-section over
# the edge's 6. From 0.7 on its line on the floor ends on the wall's far
# piece, and just over 0.7 the cut crosses the split a hair above its foot
# (7e-7 at 0.701).
for tag, mirror in (("", False), ("_mirror", True)):
    sg = -1 if mirror else 1
    be = edge_between(blind_pocket(mirror), (sg * 2, 2, 4), (sg * 2, 8, 4))
    for r in (0.5, 0.7, 0.7001, 0.701, 0.705, 0.8, 2.0):
        fillet_case("blind_pocket_split_wall%s_r%g" % (tag, r), blind_pocket(mirror), be, r,
                    "pass", 784 + (1 - math.pi / 4) * r * r * 6, 1e-4, vol_tol=1e-5, bop=True)

# At an end OnSame -- the slotted block's floor against the outer face
# (x=10), ending at the slot's wall, whose piece there is 0.7 wide; the top
# of the fin's block against the same face, ending under the fin's wall --
# the other side of the fillet runs on in its face, and the cut over a wall
# in two faces was there (#876's drafted wall). But that side's line, on a
# face that goes on past the vertex, ends on the face's far edge, and with
# neither end on an edge of the vertex the corner turned to that one for its
# face at end before it looked for the wall in two: refused from 0.7 on. Just
# over 0.7 the cut crosses the split's line within 1e-5 of its foot, where
# the new edge between the two pieces would be that short (7e-7 at 0.701,
# which BOP's check takes for no edge at all): the split starts at the
# crossing point instead. The fillet takes its cross-section over the
# edge's 3 (7 on the fin's block, further down).
for r in (0.5, 0.7, 0.7001, 0.701, 0.705, 0.8, 2.0):
    s = slotted(wall=True)
    fillet_case("slot_split_wall_mouth_r%g" % r, s, edge_between(s, (10, 3, 5), (10, 6, 5)), r,
                "pass", 1130 - (1 - math.pi / 4) * r * r * 3, 2e-4, vol_tol=1e-5, bop=True)
# With the outer face split too, by the spine's own line below the floor,
# both sides stop on edges at the spine's end, the floor's on the far piece's:
# an edge that does not reach the vertex was an obstacle to walk along, and
# the walk failed. It reaches the vertex through the wall's pieces, as the
# wall's edge in one would, and is the end -- for the walk and for the
# corner, which took the outer face's split for its face at end otherwise.
for r in (0.7001, 0.8, 2.0):
    s = slotted(wall=True, outer=True)
    fillet_case("slot_split_both_mouth_r%g" % r, s, edge_between(s, (10, 3, 5), (10, 6, 5)), r,
                "pass", 1130 - (1 - math.pi / 4) * r * r * 3, 2e-4, vol_tol=1e-5, bop=True)


def slot_by_slope(near=True, far=False, mirror=False):
    """#962's slot floor in miniature: a 10x10x5 block and on it two walls
    (y 0..4 and 7..10, up to z=10), a slot between them; the walls overhang
    the block's side x=0 by a 45 deg slope from its top edge. `near` and
    `far` split the slot's walls (y=4, y=7) by a vertical edge 0.7 from x=0."""
    s = Part.makeBox(10, 10, 5)
    side = Part.Face(Part.makePolygon([V(0, 0, 5), V(10, 0, 5), V(10, 0, 10), V(-5, 0, 10),
                                       V(0, 0, 5)]))
    for y, d in ((0, 4), (7, 3)):
        p = side.copy()
        p.translate(V(0, y, 0))
        s = s.fuse(p.extrude(V(0, d, 0)))
    s = s.removeSplitter()
    for on, y in ((near, 4), (far, 7)):
        if on:
            cut = Part.LineSegment(V(0.7, y, 5), V(0.7, y, 10)).toShape()
            s = s.generalFuse([cut])[0].Solids[0]
    return s.mirror(V(0, 0, 0), V(0, 1, 0)) if mirror else s


# The slot's floor against the block's side: four edges at either end, the
# block's side going on under the slope in line with the spine. With the
# wall in one face the end is that of four edges, one in line with the
# fillet's (IntersectMoreCorner); in two, from the piece's 0.7 on, the line
# on the floor ends on the far piece and neither side is on an edge of the
# vertex: refused. The fillet takes its cross-section over the edge's 3.
# (The walls' faces carry a location here, from the prism moved into place:
# the cut over two faces took a face's surface without it.)
for tag, kw in (("", {}), ("_mirror", {"mirror": True}), ("_both", {"far": True}),
                ("_one", {"near": False})):
    sg = -1 if kw.get("mirror") else 1
    for r in (0.5, 0.7, 0.7001, 0.701, 0.705, 0.8, 2.0, 3.0):
        s = slot_by_slope(**kw)
        fillet_case("slot_by_slope%s_r%g" % (tag, r), s,
                    edge_between(s, (0, sg * 4, 5), (0, sg * 7, 5)), r, "pass",
                    937.5 - (1 - math.pi / 4) * r * r * 3, 2e-4, vol_tol=1e-5, bop=True)


def edges_at(shape, point, along=None):
    """The 1-based indices of the edges of `shape` with an end at `point`;
    with `along`, those leaving it in one of these directions."""
    found = []
    for i, e in enumerate(shape.Edges, 1):
        ends = [v.Point for v in e.Vertexes]
        if len(ends) != 2 or not any((q - V(*point)).Length < 1e-6 for q in ends):
            continue
        d = ends[1] - ends[0] if (ends[0] - V(*point)).Length < 1e-6 else ends[0] - ends[1]
        d.normalize()
        if along is None or any((d - V(*a)).Length < 1e-3 for a in along):
            found.append(i)
    return found


def corner_case(name, shape, point, radius, vol_tol, max_tol, along=None, bop=True,
                reverse=False):
    """Every edge at `point` (or those `along` the given directions)
    filleted together: a valid solid of the volume the same corner has on
    the shape refined (removeSplitter), within vol_tol -- a plate either
    way, not the same one --, no tolerance above max_tol, nothing for BOP's
    argument check to report (bop). The edges are given in the shape's
    order, or with `reverse` the other way round."""
    step = -1 if reverse else 1
    try:
        ref = shape.removeSplitter()
        vol = ref.makeFillet(radius, [ref.Edges[i - 1]
                                      for i in edges_at(ref, point, along)[::step]]).Volume
    except Exception as e:
        report(name, False, False,
               "EXCEPTION on the refined shape: " + str(e).strip().splitlines()[-1])
        return
    fillet_case(name, shape, edges_at(shape, point, along)[::step], radius, "pass", vol,
                max_tol=max_tol, vol_tol=vol_tol, bop=bop)


# All four edges at the slot's corner, (0,4,5). The floor's fillet along the
# wall is a chain of two edges, the wall's piece at the corner 0.7 long: from
# 0.7 on it meets the fillet of the slot's edge on the block's side past the
# piece, on its second surface, and the first is dropped. It had met the
# slope's fillet on that first surface -- the meeting kept by the surface's
# index and its line's parameter, which now were the second surface's and a
# point 0.7 further on. The plate was left without its edge on the wall, the
# wall's two pieces open: invalid, 16 of volume off. The two no longer meet,
# and the plate's edge between them crosses the split. The refined shape's
# corner is another plate, 17 faces to 18, the two volumes the further apart
# the larger the radius: 0.034, 0.070, 0.109 at 0.8, 1, 1.5 (0.0999 at 1.5
# while the refined plate stood at a tolerance of 0.156, not 0.016).
for r in (0.3, 0.8, 1.0, 1.5):
    corner_case("slot_by_slope_all_four_r%g" % r, slot_by_slope(), (0, 4, 5), r,
                0.1 * max(1.0, r), 0.01)
# #962's slot floors' corners, the wall's piece 0.4606 and 0.6973 long.
for y in (13.7, 17.1, 20.3, 23.7):
    corner_case("issue962_floor_corner_y%g_all_four_r1" % y, p2, (38.5, y, 14), 1.0, 0.1, 0.01)

# Some of the four: the floor's edge along the wall with the block's side's
# under the slope, and those two with the slope's. The corner of two fillets
# apart round the vertex fails here whole or in pieces (a curve between
# them held to an edge's pcurve past its end), and is made set back, each
# fillet cut a radius from the vertex -- but not in pieces: the floor's
# fillet is a chain whose first edge, the wall's piece, is shorter than the
# setback, and the distance was measured along that edge alone (the setback
# "runs past the stripe"); and a result made was thrown away as one without
# its fillets, the short edge's midpoint being under the corner's patch
# where a fillet would have moved the surface away from it.
# From 0.75 to 0.9 and at 1.2 the patch's edge on the wall is in two, a
# short piece of it past the split. Each piece was held tangent to the wall
# (a curve over several faces always was), where the one curve of a wall in
# one face, from a fillet to a sharp edge, is held by its position alone:
# the patch came out loose, 0.014 on all its edges at 0.8, and was a
# self-intersection for BOP's check. Held by position it is as tight as on
# the shape refined.
_floor, _inline, _slope = (1, 0, 0), (0, -1, 0), (-0.7071068, 0, 0.7071068)
for r in (0.75, 0.8, 0.85, 0.9, 1.0, 1.2):
    corner_case("slot_by_slope_floor_inline_r%g" % r, slot_by_slope(), (0, 4, 5), r, 0.06, 2e-3,
                along=(_floor, _inline))
corner_case("slot_by_slope_floor_inline_slope_r1", slot_by_slope(), (0, 4, 5), 1.0, 0.15, 0.03,
            along=(_floor, _inline, _slope))
for y, inl in ((13.7, _inline), (17.1, (0, 1, 0))):
    corner_case("issue962_floor_corner_y%g_floor_inline_r1" % y, p2, (38.5, y, 14), 1.0, 0.15,
                0.03, along=(_floor, inl))

# The slope's edge with one of its neighbours, at radius 1: the slope's
# fillet is wider than the wall's piece and ends on the far one.
# With the floor's: the corner reads its edges and faces round the vertex
# starting from the first fillet's face, and the slope's fillet, given
# first, has the far piece there, a face the vertex is not on ("Failed to
# find edge"; given second it was made). Both orders, and mirrored: the
# refined shape's patch is as loose, 0.1.
# With the block's side's under the slope: set back, the floor's edge is a
# sharp one to cut a radius from the vertex, and the wall's piece of it is
# 0.7 long ("a corner's setback exceeds an edge") -- and before that, where
# the fillets meet, the face beside that edge was still the far piece, put
# there for the slope's fillet, which is cut back onto the near one.
for tag, kw in (("", {}), ("_mirror", {"mirror": True})):
    sg = -1 if kw.get("mirror") else 1
    flip = lambda d: (d[0], sg * d[1], d[2])
    for rev in (False, True):
        order = "_reversed" if rev else ""
        corner_case("slot_by_slope%s_slope_floor%s_r1" % (tag, order), slot_by_slope(**kw),
                    (0, sg * 4, 5), 1.0, 0.01, 0.15, along=(flip(_slope), flip(_floor)),
                    reverse=rev)
        corner_case("slot_by_slope%s_inline_slope%s_r1" % (tag, order), slot_by_slope(**kw),
                    (0, sg * 4, 5), 1.0, 2e-3, 0.01, along=(flip(_inline), flip(_slope)),
                    reverse=rev)


def pocket_by_split(mirror=False):
    """#962's pocket mouth in miniature: a 10x6x10 box whose front (y=0) is
    split by a vertical edge at x=5, and in the front a pocket (x 5.3..8,
    z 3..7, 2 deep) 0.3 from the split."""
    s = Part.makeBox(10, 6, 10)
    s = s.generalFuse([Part.LineSegment(V(5, 0, 0), V(5, 0, 10)).toShape()])[0].Solids[0]
    s = s.cut(Part.makeBox(2.7, 2, 4, V(5.3, 0, 3)))
    return s.mirror(V(0, 0, 0), V(1, 0, 0)) if mirror else s


# The fillet on the pocket's mouth at x=5.3: from r=0.3 its line on the front
# lies on the other piece. It takes the cross-section over the edge's 4, the
# pocket's floor and ceiling square to it. Invalid from 0.301 to 1.2, 25 or
# 6 of volume off; at 0.3, the line along the split, refused on the box as
# built (its faces REVERSED in the shell) and invalid on its mirror image.
# Up to 0.3003 the line's end and the
# split's are one vertex, of that tolerance (the corner's cut, tangent to
# the wall at the line's end, passes the split within 4e-7 there); from
# 0.3005 the closing edge is in two, 5e-4 of it on the far piece. A shape of
# its own for each case.
for tag, mirror in (("", False), ("_mirror", True)):
    pk = pocket_by_split(mirror)
    sg = -1 if mirror else 1
    pe = edge_between(pk, (sg * 5.3, 0, 3), (sg * 5.3, 0, 7))
    for r in (0.3, 0.30005, 0.3003, 0.3005, 0.303, 0.5, 0.8, 1.2):
        fillet_case("pocket_by_split%s_r%g" % (tag, r), pocket_by_split(mirror), pe, r, "pass",
                    578.4 - (1 - math.pi / 4) * r * r * 4, 1e-3 if r < 0.3005 else 2e-4,
                    vol_tol=1e-5, bop=True)
    fillet_case("pocket_by_split_chamfer%s_0.5" % tag, pocket_by_split(mirror), pe, 0.5, "pass",
                578.4 - 0.5 * 0.25 * 4, 2e-4, chamfer=True, vol_tol=1e-5, bop=True)


# #474's Fillet003 input, edge 6: its corner plate missed its boundary by 1.8
# at radius 2 -- invalid, tolerances 15 to 36, 244 too much volume at r 2.
p474 = Part.read(os.path.join(MODELS, "issue474_fillet003_base.brep"))
for r, vol in ((0.3, 1988.9101), (0.8, 1989.1235), (2.0, 1990.2561)):
    fillet_case("issue474_f003_e6_r%g" % r, p474, 6, r, "pass", vol, 0.05)
# Edge 51 of the same input, the vertical (6.415, 11.307, z 29.66..38):
# refused at every radius. IntersectMoreCorner extends the face at the
# fillet's end through a flag it never set, and the extension is skipped
# when the flag already reads non-zero -- whatever the stack held. The
# material taken is the cross-section times the edge's length to 0.1%.
e51 = edge_between(p474, (6.415306, 11.306805, 29.660692), (6.415306, 11.306805, 38.0))
for r, vol in ((0.3, 1988.711859), (0.8, 1987.728997)):
    fillet_case("issue474_f003_e51_r%g" % r, p474, e51, r, "pass", vol, 0.05, vol_tol=1e-5)

# #474's Fillet002 input, the vertical edge at (-5.494, 11.782) from z=13
# down (two edges in line, 2 and 11 long, the wall beside them in two
# coplanar pieces): at its top it ends where two faces of the helical ramp
# meet in an edge that winds 82 round the axis, five edges at the vertex.
# The fillet crosses that edge 0.07 to 0.4 from the vertex (r 0.1 to 0.5),
# and the intersection of the whole edge with the fillet did not show it:
# the two ramp faces were intersected anew and the piece of their line from
# the vertex added on top of the edge, which stayed whole -- a spike both
# faces ran up and down, "valid" for BRepCheck from 0.3 and self-intersecting
# for BOP's check, on the shape refined as well. On this shape, the edge in
# two, the piece kept of the new line was the rest of it, a turn of the ramp
# away: invalid, 707 of volume too much. Volumes: the refined shape's, now
# without the spike.
p474b = Part.read(os.path.join(MODELS, "issue474_fillet002_base.brep"))
e2 = edge_between(p474b, (-5.4940374, 11.7820012, 13.0), (-5.4940374, 11.7820012, 11.0))
for r, vol in ((0.1, 1939.439298), (0.3, 1939.216039), (0.5, 1938.769398)):
    fillet_case("issue474_f002_ramp_end_r%g" % r, p474b, e2, r, "pass", vol, 1e-4,
                vol_tol=1e-5, bop=True)
# The upright edge at the sliver of a top (13 high): the face beside the vertex
# on one side ends 0.155 from it, the fillet's line there runs on below, and
# the top's other long edge is cut by the fillet near its far end -- the piece
# kept was that end's, the top left open and the corner in it. Volumes: the
# input less the strip between the two faces and the fillet's cylinder, cut
# by booleans, to the digit shown.
e11 = edge_between(p474b, (-7.306653, 10.9367647, 13.0), (-7.306653, 10.9367647, 0.0))
for r, vol in ((0.3, 1939.2197), (0.8, 1937.8196)):
    fillet_case("issue474_f002_sliver_top_r%g" % r, p474b, e11, r, "pass", vol, 1e-4,
                vol_tol=1e-4, bop=True)

# The same foot made small: an arm (a prism of a quadrilateral) fused to a
# block, the seam between their bottoms running from y=27.2 to y=10.2 -- the
# direction that put the second corner's point past the seam's end.
def arm_on_block():
    pts = [V(17.356, -9.425, -9.75), V(38.5, 10.2, -9.75), V(38.5, 27.2, -9.75),
           V(10.898, 16.471, -9.75)]
    arm = Part.Face(Part.makePolygon(list(reversed(pts)) + [pts[-1]])).extrude(V(0, 0, 6))
    bp = [V(38.5, 27.2, -9.75), V(38.5, 10.2, -9.75), V(50, 10.2, -9.75), V(50, 27.2, -9.75)]
    return Part.Face(Part.makePolygon(bp + [bp[0]])).extrude(V(0, 0, 6)).fuse(arm)


ab = arm_on_block()
foot = [edge_between(ab, (38.5, 27.2, -3.75), (38.5, 27.2, -9.75)),
        edge_between(ab, (38.5, 10.2, -3.75), (38.5, 10.2, -9.75))]
for r in (0.5, 0.8, 1.5):
    alone = sum(ab.Volume - ab.makeFillet(r, [ab.Edges[i - 1]]).Volume for i in foot)
    fillet_case("arm_on_block_foot_r%g" % r, ab, foot, r, "pass", ab.Volume - alone)

# Edge 36 alone at its top (38.5,27.2,-3.75): the arm's side meets the block's
# side at 21 degrees, and above the arm the block goes on, its side y=27.2 two
# coplanar faces split at the arm's top. The corner is a GeomPlate patch; below
# radius 0.42 a curve of its boundary had no projection on the plate's first
# surface, and the projection threw where Perform tries another surface.
# The plate went since (the ceiling, below arm_on_tall_block): the end is
# exact, and what the fillet takes -- 0.0012 of 11584 at 0.3 -- is the check,
# with BOP's and a tolerance no plate would keep.
def round_cut(shape, edge_index, size, chamfer=False):
    """What a fillet of radius `size` takes of a straight convex edge between
    two planes, cut square at its ends: the corner's section, r^2 (tan a - a)
    with a half the angle between the faces' normals, over the edge's length.
    A chamfer of distance `size`: d^2 sin(2a) / 2."""
    e = shape.Edges[edge_index - 1]
    n = [f.normalAt(0, 0) for f in shape.ancestorsOfType(e, Part.Face)]
    a = n[0].getAngle(n[1]) / 2
    area = size * size * (math.sin(2 * a) / 2 if chamfer else math.tan(a) - a)
    return area * e.Length


e36 = edge_between(p2, (38.5, 27.2, -3.75), (38.5, 27.2, -9.75))
# (the model read anew: a fillet leaves its tolerances on what the result
# shares with the input, and p2 has been filleted above)
for r in (0.1, 0.3, 0.8, 2.0):
    q2 = Part.read(os.path.join(MODELS, "issue962_pocket002.brep"))
    fillet_case("issue962_e36_r%g" % r, q2, e36, r, "pass", q2.Volume - round_cut(q2, e36, r),
                1e-6, vol_tol=1e-6, bop=True)
for d in (0.3, 2.0):
    fillet_case("issue962_e36_chamfer_d%g" % d, p2, e36, d, "pass",
                p2.Volume - round_cut(p2, e36, d, True), 2e-4, chamfer=True, vol_tol=1e-6,
                bop=True)


def arm_on_tall_block(split=True, near=False):
    """split: the block's side y=27.2 split at the arm's top; near: its side y=10.2"""
    pts = [V(17.356, -9.425, -9.75), V(38.5, 10.2, -9.75), V(38.5, 27.2, -9.75),
           V(10.898, 16.471, -9.75)]
    arm = Part.Face(Part.makePolygon(list(reversed(pts)) + [pts[-1]])).extrude(V(0, 0, 6))
    bp = [V(38.5, 27.2, -9.75), V(38.5, 10.2, -9.75), V(50, 10.2, -9.75), V(50, 27.2, -9.75)]
    s = Part.Face(Part.makePolygon(bp + [bp[0]])).extrude(V(0, 0, 23.75)).fuse(arm)
    cuts = []
    if split:
        cuts.append(Part.LineSegment(V(38.5, 27.2, -3.75), V(50, 27.2, -3.75)).toShape())
    if near:
        cuts.append(Part.LineSegment(V(38.5, 10.2, -3.75), V(50, 10.2, -3.75)).toShape())
    if cuts:
        s = s.generalFuse(cuts)[0].Solids[0]
    return s


# The fillet ends in the plane of the arm's top, under the block's wall
# x=38.5, which stands on that plane: its section cuts the arm's top as far
# as the wall's edge, and from there on it runs under the wall, where the
# body is closed by a face in the same plane turned the other way, a ceiling
# (CeilingAtEnd). A plate over the whole corner stood there before, lying
# on the arm's top for the part of it this side of the wall: valid, 0.02
# to 0.06 of tolerance, 0.007 of volume off at radius 2 and refused by
# BOP's check. What the fillet takes is the corner's section over the
# edge's 6, to the last digit.
atb = arm_on_tall_block()
top = edge_between(atb, (38.5, 27.2, -3.75), (38.5, 27.2, -9.75))
for r in (0.1, 0.3, 0.8, 2.0):
    fillet_case("arm_on_tall_block_r%g" % r, atb, top, r, "pass",
                atb.Volume - round_cut(atb, top, r), 1e-6, vol_tol=1e-6, bop=True)
for d in (0.3, 2.0):
    fillet_case("arm_on_tall_block_chamfer_d%g" % d, atb, top, d, "pass",
                atb.Volume - round_cut(atb, top, d, True), 2e-4, chamfer=True, vol_tol=1e-6,
                bop=True)
# The block's side one face: the line on it runs on up past the arm's top,
# and the arm's top, extended to meet it, crossed its own edge under the
# block's wall -- invalid at every radius. The line is cut where it crosses
# the plane of the arm's top, and the ceiling's third side is a new edge on
# the block's side, from there to the vertex.
atb = arm_on_tall_block(split=False)
top = edge_between(atb, (38.5, 27.2, -3.75), (38.5, 27.2, -9.75))
for r in (0.1, 0.3, 0.5, 0.8, 2.0):
    fillet_case("arm_on_tall_block_whole_r%g" % r, atb, top, r, "pass",
                atb.Volume - round_cut(atb, top, r), 1e-6, vol_tol=1e-6, bop=True)
for d in (0.3, 2.0):
    fillet_case("arm_on_tall_block_whole_chamfer_d%g" % d, atb, top, d, "pass",
                atb.Volume - round_cut(atb, top, d, True), 2e-4, chamfer=True, vol_tol=1e-6,
                bop=True)
# The mirror corner, the block's edge x=38.5 y=10.2 coming down onto the arm's
# top: there the arm's top, extended, is the floor of the fillet's end and
# crosses nothing, and must stay the exact plane it is (a plate in its place
# misses by 1e-2): a quarter-round's section over the edge's 17.75.
low = edge_between(atb, (38.5, 10.2, -3.75), (38.5, 10.2, 14))
for r in (0.3, 1.0, 2.0):
    fillet_case("arm_on_tall_block_down_r%g" % r, atb, low, r, "pass",
                atb.Volume - (1 - math.pi / 4) * r * r * 17.75, max_tol=1e-3)
# The corner under the wall again (the ceiling, above): mirror images, for
# the fillet's other side on the arm and its other end at the corner.
for split in (True, False):
    for tag, normals in (("x", [(1, 0, 0)]), ("z", [(0, 0, 1)]), ("xz", [(1, 0, 0), (0, 0, 1)])):
        mirrored = arm_on_tall_block(split=split)
        ends = [V(38.5, 27.2, -3.75), V(38.5, 27.2, -9.75)]
        for n in normals:
            mirrored = mirrored.mirror(V(0, 0, 0), V(*n))
            ends = [V(q.x * (1 - 2 * n[0]), q.y, q.z * (1 - 2 * n[2])) for q in ends]
        mtop = edge_between(mirrored, tuple(ends[0]), tuple(ends[1]))
        for r in (0.3, 2.0):
            fillet_case("arm_on_tall_block%s_mirror_%s_r%g" % ("" if split else "_whole", tag, r),
                        mirrored, mtop, r, "pass", mirrored.Volume - round_cut(mirrored, mtop, r),
                        1e-6, vol_tol=1e-6, bop=True)


def arm_tilted_under_block(normal):
    """The arm on the tall block with its top a plane of the given normal
    through the corner (38.5, 27.2, -3.75), not square to the edge between
    the arm's side and the block's."""
    pts = [V(17.356, -9.425, -9.75), V(38.5, 10.2, -9.75), V(38.5, 27.2, -9.75),
           V(10.898, 16.471, -9.75)]
    arm = Part.Face(Part.makePolygon(list(reversed(pts)) + [pts[-1]])).extrude(V(0, 0, 12))
    n = V(*normal).normalize()
    plane = Part.makePlane(400, 400, V(-200, -200, 0))
    plane.Placement = App.Placement(V(38.5, 27.2, -3.75), App.Rotation(V(0, 0, 1), n))
    arm = arm.common(plane.extrude(n * -40))
    bp = [V(38.5, 27.2, -9.75), V(38.5, 10.2, -9.75), V(50, 10.2, -9.75), V(50, 27.2, -9.75)]
    return Part.Face(Part.makePolygon(bp + [bp[0]])).extrude(V(0, 0, 23.75)).fuse(arm)


def tilted_cut(radius, normal):
    """What the fillet takes there: the corner's section times the height
    of the tilted plane over the section's centroid."""
    u1 = V(10.898 - 38.5, 16.471 - 27.2, 0).normalize()
    u2 = V(1, 0, 0)
    a = (math.pi - u1.getAngle(u2)) / 2
    bis = (u1 + u2).normalize()
    area = radius * radius * (math.tan(a) - a)
    t = radius * math.tan(a)
    d = radius / math.cos(a)
    # the kite between the tangent points less the sector of the arc
    c = (radius * radius * math.tan(a) * (t * math.sin(a) + d) / 3
         - radius * radius * a * (d - 2 * radius * math.sin(a) / (3 * a))) / area
    return area * (6.0 - (normal[0] * bis.x + normal[1] * bis.y) * c / normal[2])


# The arm's top tilted: the fillet's line on the block's side crosses its
# plane above or below the corner, the section is an arc of an ellipse, and
# the ceiling tilts with the top.
for tag, normal in (("up_x", (0.08, 0, 1)), ("down_x", (-0.08, 0, 1)), ("up_y", (0, 0.08, 1)),
                    ("down_y", (0, -0.08, 1)), ("skew", (0.06, -0.06, 1))):
    tilted = arm_tilted_under_block(normal)
    ttop = [i for i, e in enumerate(tilted.Edges, 1)
            if abs(e.Length - 6) < 1e-6
            and e.distToShape(Part.Vertex(V(38.5, 27.2, -6.75)))[0] < 1e-6][0]
    for r in (0.3, 2.0):
        fillet_case("arm_tilted_under_block_%s_r%g" % (tag, r), tilted, ttop, r, "pass",
                    tilted.Volume - tilted_cut(r, normal), 1e-6, vol_tol=1e-6, bop=True)

# A fin padded flush with the block's side: the outer face is two faces, the
# fin's and the block's, split at the floor's height, and the fillet's line on
# the fin's face ends on that split. It must take what it takes from the slot.
def fin_on_block(wall=False, arc=False):
    if arc:  # the fin's top an arc tangent to its outer face
        prof = Part.Wire([Part.LineSegment(V(0, 0, 5), V(10, 0, 5)).toShape(),
                          Part.LineSegment(V(10, 0, 5), V(10, 0, 8)).toShape(),
                          Part.Arc(V(10, 0, 8), V(4 + 6 * 0.5 ** 0.5, 0, 8 + 6 * 0.5 ** 0.5),
                                   V(4, 0, 14)).toShape(),
                          Part.LineSegment(V(4, 0, 14), V(0, 0, 14)).toShape(),
                          Part.LineSegment(V(0, 0, 14), V(0, 0, 5)).toShape()])
        f = Part.Face(prof).extrude(V(0, 3, 0))
    else:
        f = Part.makeBox(10, 3, 9, V(0, 0, 5))
    s = Part.makeBox(10, 10, 5).fuse(f)
    if wall:
        s = s.generalFuse([Part.LineSegment(V(9.3, 3, 5), V(9.3, 3, 20)).toShape()])[0].Solids[0]
    return s


for r in (0.3, 0.8, 2.0):
    taken = plain.Volume - plain.makeFillet(r, [plain.Edges[spine - 1]]).Volume
    fin = fin_on_block()
    fillet_case("fin_on_block_r%g" % r, fin, edge_between(fin, (10, 3, 5), (10, 3, 14)), r,
                "pass", fin.Volume - taken)
fin = fin_on_block(arc=True)
for r in (0.3, 0.8):
    fillet_case("fin_arc_on_block_r%g" % r, fin, edge_between(fin, (10, 3, 5), (10, 3, 8)), r,
                "pass")
# and its wall split as the slot's: wider than the wall's piece from 0.7 on,
# the fillet's line on the wall leaves the piece where the fin's face ends
fin = fin_on_block(wall=True)
for r in (0.3, 0.8, 2.0):
    taken = plain.Volume - plain.makeFillet(r, [plain.Edges[spine - 1]]).Volume
    fillet_case("fin_on_block_wall_r%g" % r, fin, edge_between(fin, (10, 3, 5), (10, 3, 14)), r,
                "pass", fin.Volume - taken)
# exactly as wide as the wall's piece, and within the walk's tolerance (1e-4)
# of it: the fillet's line on the wall runs along the split itself, the
# narrow piece and the split go under the fillet
for r in (0.7, 0.70001, 0.7001):
    taken = plain.Volume - plain.makeFillet(r, [plain.Edges[spine - 1]]).Volume
    for tag, s in (("slot_split_wall", slotted(wall=True)),
                   ("slot_split_both", slotted(wall=True, outer=True)),
                   ("fin_on_block_wall", fin)):
        fillet_case("%s_r%g" % (tag, r), s, edge_between(s, (10, 3, 5), (10, 3, 14)), r, "pass",
                    s.Volume - taken)
# the block's top against its side (x=10), ending under the fin's wall, the
# wall's piece there 0.7 wide: the cut over the wall's two pieces (above,
# the slot's mouth)
for r in (0.7001, 0.8, 2.0):
    s = fin_on_block(wall=True)
    fillet_case("fin_on_block_wall_top_r%g" % r, s, edge_between(s, (10, 3, 5), (10, 10, 5)), r,
                "pass", 770 - (1 - math.pi / 4) * r * r * 7, 2e-4, vol_tol=1e-5, bop=True)
# and a chamfer of that size, which walks the same way: a triangle of d^2/2
# over the spine's 9
for d in (0.7, 0.70001, 0.7001):
    s = slotted(wall=True)
    fillet_case("slot_split_wall_chamfer_d%g" % d, s, edge_between(s, (10, 3, 5), (10, 3, 14)), d,
                "pass", s.Volume - 4.5 * d * d, chamfer=True)

# realthunder/FreeCAD#876's first Fillet input: the four edges at the corner
# (17,16.75,3). The two-stripe corner there has its common points on two
# different edges and filled along a pivot it does not have -- a null
# dereference that took the process down; it failed after that fix, its
# far corner (-17,16.75,3) leaving the stripe's end without a point. The
# corner setback fallback makes it: both corners set back where the fillets
# meet (fcad docs/CornerBlending.md section 9). The edges run between nearly
# coplanar drafted walls, so the fillets move the volume by thousandths.
# At 0.3 the fillet on the long edge (-17..17, z=3) is the one of
# issue876_post_foot_e10_r0.3 below, a few thousandths wide. Its lines
# ended in one vertex, 0.0026 from each (0.00524), and BOP's check found
# an edge too small there -- the fillet split where it is no narrower
# (issue876_kink_* below).
p876 = Part.read(os.path.join(MODELS, "issue876_fillet_base.brep"))
c876 = [edge_between(p876, (17, 16.75, 0), (17, 16.75, 3)),
        edge_between(p876, (-17, 16.75, 3), (17, 16.75, 3)),
        edge_between(p876, (19.238761, 15.746985, 3), (17, 16.75, 3)),
        edge_between(p876, (17, 16.75, 3), (17, 16.442791, 20.6))]
for r, vol, tol, bop in ((0.3, 8665.7840, 1e-3, True), (1.0, 8665.7870, None, False)):
    fillet_case("issue876_corner4_r%g" % r, p876, c876, r, "pass", vol, tol, bop=bop)


def refused_case(name, shape, edge_index, radius, chamfer=False):
    """The fillet (makeChamfer with chamfer=True) is refused, and the input
    left as it was."""
    before = signature(shape)
    indices = edge_index if isinstance(edge_index, list) else [edge_index]
    # the edges looked up outside the try: a wrong index is the case's fault,
    # not a refusal; only the kernel's own refusal (Part.OCCError) counts
    edges = [shape.Edges[i - 1] for i in indices]
    make = shape.makeChamfer if chamfer else shape.makeFillet
    try:
        r = make(radius, edges)
        ok, detail = False, "made: valid=%s vol=%.4f" % (r.isValid(), r.Volume)
    except Part.OCCError as e:
        ok, detail = True, "refused: " + str(e).strip().splitlines()[-1]
    if signature(shape) != before:
        ok, detail = False, "input changed; " + detail
    report(name, ok, False, detail)


# With FreeCAD's Part preference FilletCornerSetbackFallback at 0 the fallback
# is off, and the corner fails as it did.
_part_params = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Part")
_had_fallback = "FilletCornerSetbackFallback" in _part_params.GetFloats()
_fallback = _part_params.GetFloat("FilletCornerSetbackFallback", 2.0)
_part_params.SetFloat("FilletCornerSetbackFallback", 0.0)
try:
    refused_case("issue876_corner4_r1_no_fallback", p876, c876, 1.0)
finally:
    if _had_fallback:
        _part_params.SetFloat("FilletCornerSetbackFallback", _fallback)
    else:
        _part_params.RemFloat("FilletCornerSetbackFallback")

# #474's Fillet002 input, a box corner at the top of the block's upright edge
# (-7.307, 10.937): the edge along the top in the same face is 0.155 long.
# The upright edge's fillet alone, at 0.3 or 1, takes that edge whole at its
# end; the two together have no corner to make -- their lines on the common
# face do not meet -- and the plate made one over the short fillet's own
# end: invalid, upstream as well. Refused (with the setback fallback on, as
# FreeCAD has it, too); the upright edge alone is made.
p474c = Part.read(os.path.join(MODELS, "issue474_fillet002_base.brep"))
_v7 = (-7.3066530, 10.9367647, 13.0)
_up = edge_between(p474c, _v7, (-7.3066530, 10.9367647, 0.0))
_top = edge_between(p474c, (-7.2412455, 10.7964979, 13.0), _v7)
for r, vol in ((0.3, 1939.2197), (1, 1936.9339)):
    refused_case("issue474_f002_whole_in_end_r%g" % r, p474c, [_up, _top], r)
    fillet_case("issue474_f002_upright_alone_r%g" % r, p474c, _up, r, "pass", vol, 1e-4,
                vol_tol=1e-4, bop=True)

# A post on a plate, the plate's side running tangent into its round end
# under the post: the plate's top edge along that side ends where the top
# face pinches out against the post's base. The fillet is cut by the post's
# cylinder, its end on the side face lands on the edge where the side meets
# the round end, and the piece of that edge above the end bounds the round
# end and the post's wall (one cylinder). That piece was left in the side
# face as well: a wire running up to the plate's top and back down, an
# invalid shape at every radius. The corner kept by the cut is the corner
# prism inside the cylinder, which gives the volume.
def post_on_plate(draft=0.0, turn=0.0):
    plate = Part.makeCylinder(3, 3).fuse(Part.makeBox(12, 6, 3, V(-12, -3, 0))).removeSplitter()
    if draft:
        post = Part.makeCone(3, 3 - 15 * math.tan(math.radians(draft)), 15, V(0, 0, 3))
    else:
        post = Part.makeCylinder(3, 15, V(0, 0, 3))
    if turn:
        post.rotate(V(0, 0, 0), V(0, 0, 1), turn)
    return plate.fuse(post)


pp = post_on_plate()
side = edge_between(pp, (-12, -3, 3), (0, -3, 3))
for r in (0.1, 0.6, 2.0):
    corner = Part.makeBox(12, r, r, V(-12, -3, 3 - r)).cut(
        Part.makeCylinder(r, 12, V(-12, -3 + r, 3 - r), V(1, 0, 0)))
    removed = corner.cut(Part.makeCylinder(3, 10, V(0, 0, -2))).Volume
    fillet_case("post_on_plate_r%g" % r, pp, side, r, "pass", pp.Volume - removed)

# The post's own seam through the edge's end (the post turned three
# quarters, its seam at (0,-3)): the cut ends on the seam at u=2pi, and the
# extension from there to the vertex was put at u=0, Arcprol's parameter at
# the vertex -- the post's wire did not close in its domain, and the face
# came out inside out, 12 taken at radius 0.6. The same volume as the post
# turned any other way.
pps = post_on_plate(turn=270)
for r in (0.1, 0.6, 2.0):
    corner = Part.makeBox(12, r, r, V(-12, -3, 3 - r)).cut(
        Part.makeCylinder(r, 12, V(-12, -3 + r, 3 - r), V(1, 0, 0)))
    removed = corner.cut(Part.makeCylinder(3, 10, V(0, 0, -2))).Volume
    fillet_case("post_seam_on_plate_r%g" % r, pps, edge_between(pps, (-12, -3, 3), (0, -3, 3)), r,
                "pass", pps.Volume - removed)

# The same with a drafted post (1 deg): the post's wall is a cone, the round
# end below it a cylinder. The edge between them is sharp now, the vertex
# has four sharp edges, and the spine's end was a break point: the walk ran
# on along the post's base edge and the corner went to the plate, refused.
# With the side and the round end taken as one wall, the vertex is the
# undrafted post's corner, and the fillet is cut by the post's cone carried
# on below its base: the corner prism outside that cone, which gives the
# volume.
ppd = post_on_plate(1.0)
for r in (0.1, 0.6, 2.0):
    corner = Part.makeBox(12, r, r, V(-12, -3, 3 - r)).cut(
        Part.makeCylinder(r, 12, V(-12, -3 + r, 3 - r), V(1, 0, 0)))
    t = math.tan(math.radians(1.0))
    removed = corner.cut(Part.makeCone(3 + 5 * t, 3, 5, V(0, 0, -2))).Volume
    fillet_case("post_draft_on_plate_r%g" % r, ppd,
                edge_between(ppd, (-12, -3, 3), (0, -3, 3)), r, "pass", ppd.Volume - removed)
    # and its seam at the vertex, both at once
    ppds = post_on_plate(1.0, 270)
    fillet_case("post_draft_seam_on_plate_r%g" % r, ppds,
                edge_between(ppds, (-12, -3, 3), (0, -3, 3)), r, "pass", ppds.Volume - removed)
# steeper drafts, the corner the same
for d in (3.0, 10.0):
    ppd = post_on_plate(d)
    r = 0.6
    corner = Part.makeBox(12, r, r, V(-12, -3, 3 - r)).cut(
        Part.makeCylinder(r, 12, V(-12, -3 + r, 3 - r), V(1, 0, 0)))
    t = math.tan(math.radians(d))
    removed = corner.cut(Part.makeCone(3 + 5 * t, 3, 5, V(0, 0, -2))).Volume
    fillet_case("post_draft%g_on_plate_r%g" % (d, r), ppd,
                edge_between(ppd, (-12, -3, 3), (0, -3, 3)), r, "pass", ppd.Volume - removed)

# The drafted post's corner as #876 has it: a 1 deg drafted post whose
# base is a circle of radius 3 (the plate's round end, as above) from the
# plate's side over 41 deg of arc on the plate's top, then a straight wall
# tangent to it -- a cone and a plane -- the far side closed by a second
# tangent wall: a teardrop. The fillet's line on the top, at y=-3+r, stays
# on the arc up to r = 3(1-cos 41deg) = 0.736; past that it ends on the
# plane's base edge, a face that does not hold the vertex. The cut then runs
# over the plane and on over the cone, the two pieces meeting where the cut
# crosses the cone/plane edge carried on below the plate's top; that piece
# of the edge bounds both. The removed volume is the corner prism outside
# the post carried on below its base, by booleans. Refused before at r>=0.8.
def teardrop_post(z0, z1, draft=1.0, arc=41.0):
    """The post between heights z0 and z1, its outline at z=3 as above."""
    t1 = -math.pi / 2 - math.radians(arc)
    q0 = V(3 * math.cos(t1), 3 * math.sin(t1), 0) + V(math.sin(t1), -math.cos(t1), 0) * 6
    g = math.acos(3 / math.hypot(q0.x, q0.y))
    t2 = math.atan2(q0.y, q0.x) + g
    if abs(math.cos(t2 - t1) - 1) < 1e-9:  # that is the first tangent's point
        t2 -= 2 * g
    while t2 < t1:
        t2 += 2 * math.pi
    tan = math.tan(math.radians(draft))

    def section(z):
        rad = 3 - (z - 3) * tan
        n1, n2 = V(math.cos(t1), math.sin(t1), 0), V(math.cos(t2), math.sin(t2), 0)
        det = n1.x * n2.y - n1.y * n2.x
        q = V(rad * (n2.y - n1.y) / det, rad * (n1.x - n2.x) / det, z)
        return rad, V(rad * math.cos(t1), rad * math.sin(t1), z), \
            V(rad * math.cos(t2), rad * math.sin(t2), z), q

    def cap(z, rad, a, b, q):
        tm = (t1 + t2) / 2
        arc_ = Part.Arc(a, V(rad * math.cos(tm), rad * math.sin(tm), z), b).toShape()
        return Part.Face(Part.Wire([arc_, Part.makeLine(b, q), Part.makeLine(q, a)]))

    r0, a0, b0, q0_ = section(z0)
    r1, a1, b1, q1_ = section(z1)
    cone = Part.Cone(V(0, 0, z0), V(0, 0, z1), r0, r1)
    faces = [cone.toShape(t1 + 2 * math.pi, t2 + 2 * math.pi, 0,
                          (z1 - z0) / math.cos(math.radians(draft))),
             Part.Face(Part.makePolygon([a0, q0_, q1_, a1, a0])),
             Part.Face(Part.makePolygon([q0_, b0, b1, q1_, q0_])),
             cap(z0, r0, a0, b0, q0_), cap(z1, r1, a1, b1, q1_)]
    shell = Part.Shell(faces)
    shell.sewShape()
    solid = Part.Solid(shell)
    if solid.Volume < 0:
        solid.reverse()
    return solid


def teardrop_case(name, r, draft=1.0, arc=41.0, mirror=False, nurbs=False):
    plate = Part.makeCylinder(3, 3).fuse(Part.makeBox(12, 6, 3, V(-12, -3, 0))).removeSplitter()
    post = teardrop_post(3, 18, draft, arc)
    carried = teardrop_post(-2, 18, draft, arc)
    if nurbs:
        post = post.toNurbs()
    shape = plate.fuse(post).removeSplitter()
    corner = Part.makeBox(12, r, r, V(-12, -3, 3 - r)).cut(
        Part.makeCylinder(r, 12, V(-12, -3 + r, 3 - r), V(1, 0, 0)))
    removed = corner.cut(carried).Volume
    sy = -3
    if mirror:
        shape = shape.mirror(V(0, 0, 0), V(0, 1, 0))
        sy = 3
    # the default GProp of the B-spline post is off by more than RELTOL;
    # its volume was checked with adaptive GProp (README)
    fillet_case(name, shape, edge_between(shape, (-12, sy, 3), (0, sy, 3)), r, "pass",
                None if nurbs else shape.Volume - removed)


for r in (0.6, 0.8, 1.0, 2.0):
    teardrop_case("post_draft_plane_on_plate_r%g" % r, r)
teardrop_case("post_draft_plane_mirror_r1", 1.0, mirror=True)
teardrop_case("post_draft10_plane_on_plate_r1", 1.0, draft=10.0)
teardrop_case("post_draft_plane_arc20_r0.6", 0.6, arc=20.0)
teardrop_case("post_draft_plane_nurbs_r1", 1.0, nurbs=True)

# The plate's other side, y=3, where the cone's arc on the top is 12 deg:
# from radius 0.9 the line crosses onto the far wall well away from the
# vertex. With the post's faces B-splines, the cone's surface carried on
# curves back to meet the fillet's line on the side 8 away from the vertex,
# nearer to where the walk ended; the cut ran there, inside out (volume up
# by 50). The cut's end must lie beside the cone's arc: refused, as before.
plate_n = Part.makeCylinder(3, 3).fuse(Part.makeBox(12, 6, 3, V(-12, -3, 0))).removeSplitter()
tear_n = plate_n.fuse(teardrop_post(3, 18).toNurbs()).removeSplitter()
sound_case("post_draft_plane_nurbs_far_side_r1", tear_n,
           edge_between(tear_n, (-12, 3, 3), (0, 3, 3)), 1.0)

# realthunder/FreeCAD#876's Fillet002: its input (Fillet001's result) has a
# plate whose top outline -- two lines and an arc, one tangent chain --
# runs at both ends into a drafted corner of the tall body, the plate's side
# tangent to the round end below it: the drafted post's corner above. Two
# of its walls are cones trimmed at the plate's top, which kept the cut
# from reaching below it. The volumes are from the fixes, adaptive GProp; a
# Pappus estimate along the chain is short of them by an end loss in
# proportion to the cut's length at both radii. From radius 0.8 on, the line
# on the top passes the cone's base arc onto the drafted wall's plane, which
# the cone continues tangent to: the cut runs over both (see the teardrop
# post above). At radius 1.2 one corner's edge from the vertex down the side
# missed the vertex by 6e-14 more than the tolerance it gave the vertex.
p876b = Part.read(os.path.join(MODELS, "issue876_fillet002_base.brep"))
e876b = [edge_between(p876b, (-19.238761, -15.746985, 3), (-30.167832, -3.494723, 3)),
         edge_between(p876b, (30.167832, -3.494723, 3), (19.238761, -15.746985, 3))]
for r, taken in ((0.3, 1.51537), (0.6, 5.97437), (0.8, 10.53689), (1.0, 16.34631),
                 (1.5, 36.20076), (2.0, 63.44643), (1.2, 23.38327)):
    fillet_case("issue876_fillet002_r%g" % r, p876b, e876b, r, "pass", p876b.Volume - taken,
                2e-4)

# #876's Fillet input again, two edges at once: the plate's top edge along its
# side and the post's base arc on the top beside it, a convex and a concave
# fillet ending at one vertex of four sharp edges. The first end is OnSame
# there across the tangent split (the drafted wall's rule above), which the
# plate of two stripes cannot take: at radius 1 the result was inside out
# (volume -2e10), refused before that rule and now again. At 0.6 the plate is
# made of two break points, inside out the same, before the rule as well:
# the two fillets are tangent at the vertex, which skips the search for a
# plate boundary over several faces, and the post's fillet, cut back past
# its round end onto its plane, had its end on the plane read as a point of
# the round end's B-spline. Refused now. The same at the plate's other
# corners, and on Fillet002's input with the drafted post.
for a, b, c, d in (((19.238761, 15.746985, 3), (30.167832, 3.494723, 3),
                    (20, 13.750014, 3), (19.238761, 15.746985, 3)),
                   ((-30.167832, 3.494723, 3), (-19.238761, 15.746985, 3),
                    (-19.238761, 15.746985, 3), (-20, 13.750021, 3))):
    pair = [edge_between(p876, a, b), edge_between(p876, c, d)]
    tag = "x%+d" % round(a[0] if abs(a[0]) < 20 else b[0])
    sound_case("issue876_side_and_post_%s_r1" % tag, p876, pair, 1.0)
    sound_case("issue876_side_and_post_%s_r0.6" % tag, p876, pair, 0.6)
pair = [edge_between(p876, (-20, -13.75, 3), (-19.238761, -15.746985, 3)),
        edge_between(p876, (-19.238761, -15.746985, 3), (-30.167832, -3.494723, 3))]
sound_case("issue876_side_and_post_x-19_y-16_r1", p876, pair, 1.0)
pair = [edge_between(p876b, (19.238761, -15.746985, 3), (20, -13.75, 3)),
        edge_between(p876b, (30.167832, -3.494723, 3), (19.238761, -15.746985, 3))]
for r in (0.6, 1.0):
    sound_case("issue876_fillet002_side_and_post_r%g" % r, p876b, pair, r)

# realthunder/FreeCAD#631's Fillet002 input: a chain of six edges round a
# slanted arm, ending at (44, 36.33, 92) on the end face x = 44. The corner
# there extends the arm's round end, a circle, past the vertex to the point
# where the fillet's line on the round meets the end face; that point is
# off the circle by 3.7e-7 and the circle's edge kept 1e-7, so BRepCheck,
# finding the cut and the circle, tangent there, crossing 1.3e-3 from the
# vertex, would not excuse it: invalid at 0.8 and 2.
p631 = Part.read(os.path.join(MODELS, "issue631_fillet002_base.brep"))
e631 = edge_between(p631, (-7.5, -14.823467, 15.553928), (-7.5, -15.0, 11.398326))
for r, vol in ((0.8, 41530.1861), (2.0, 41484.0873)):
    fillet_case("issue631_fillet002_r%g" % r, p631, e631, r, "pass", vol)

# FreeCAD's PartDesign case 5829: a box with a wedge on its back, filleted
# all round at 8 (models/case5829_box.brep, the Box feature's solid, and the
# twelve edges its Fillet takes). Its corner plates, held tangent, miss their
# boundary by 0.45-0.49% of the radius; the plate fallback at a fixed 1e-3
# rebuilt them creased, and no thickness of the creased solid came out. A
# miss under 1% of the smallest radius at the corner keeps the tangent plate
# (ChFi3d_Builder::SetPlateG0FallbackRatio): the fillet is valid and its large
# face removed, 1 inward, it thickens.
c5829 = Part.read(os.path.join(MODELS, "case5829_box.brep"))
e5829 = [edge_between(c5829, a, b) for a, b in (
    ((96, 0, 0), (96, -10, 0)), ((96, 0, 0), (86, 25, 10)), ((86, 25, 116), (86, 25, 10)),
    ((86, 25, 10), (10, 25, 10)), ((0, 0, 0), (10, 25, 10)), ((0, 0, 0), (0, -10, 0)),
    ((10, 25, 116), (10, 25, 10)), ((0, 0, 126), (10, 25, 116)), ((86, 25, 116), (10, 25, 116)),
    ((96, 0, 126), (96, -10, 126)), ((96, 0, 126), (86, 25, 116)), ((0, 0, 126), (0, -10, 126)))]
fillet_case("case5829_r8", c5829, e5829, 8.0, "pass", 367718.5802)
try:
    f5829 = c5829.makeFillet(8.0, [c5829.Edges[i - 1] for i in e5829])
    opening = max((x for x in f5829.Faces if isinstance(x.Surface, Part.Plane)
                   and abs(x.CenterOfMass.y + 10.0) < 1e-7), key=lambda x: x.Area)
    t5829 = f5829.makeThickness([opening], -1.0, 1e-3)
    ok = t5829.isValid() and len(t5829.Solids) == 1
    report("case5829_r8_thickness", ok, False,
           "vol=%.4f" % t5829.Volume if ok else "invalid result, vol=%.4g" % t5829.Volume)
except Exception as e:
    report("case5829_r8_thickness", False, False,
           "EXCEPTION " + str(e).strip().splitlines()[-1])

# #474's Fillet001 (models/issue474_fillet001_base.brep): the edge up the
# ramp's side ends at a vertex of four sharp edges whose face beside the
# spine runs on, tangent, into the next -- a corner of three for the
# drafted wall's rule above. At radius 0.3 that corner is made (the result
# tighter: tolerance 0.013 before, 1e-4 now). At radius 1 the fillet's line
# on the face that runs on meets the face at end at its very last point:
# found the last digit past it, the crossing was taken for none ("bouchon
# non ecrit") and the fillet computed again with the end a break point --
# valid, with a tolerance of 0.025, and failing BOP's check. The crossing
# taken (6163e90334), the corner is made there too: 1e-4, the check clean,
# 0.012 more of volume taken.
p474b = Part.read(os.path.join(MODELS, "issue474_fillet001_base.brep"))
e474b = edge_between(p474b, (-9, 0, 11), (-9, 0, 16))
for r, taken in ((0.3, 3.56632), (1.0, 40.26510)):
    fillet_case("issue474_f001_e12_r%g" % r, p474b, e474b, r, "pass", p474b.Volume - taken,
                max_tol=2e-4, vol_tol=1e-3, bop=True)
# The bar's long edges (21 and 26) at 2, a hair over its side's 1.9922: the
# walk leaves the side, too narrow, for the face beyond where there is one,
# and makes the edge's last seventh (z 11..13 of -0.18..12.82). A surface
# that stops so far short of its spine's end is no fillet of the edge:
# refused. The corner at the made end -- its cut over the end face and the
# ramp tangent to it -- failed on a face's location and so hid it; with the
# cut put right, the fillet of a seventh came out, invalid.
for i in (21, 26):
    sound_case("issue474_f001_e%d_r2" % i, p474b, i, 2.0)

# Two edges filleted together at a vertex where a split of a wall kept in
# coplanar pieces ends (bodies without Refine): the vertex sweep's results
# invalid only in pieces (sweep/README.md), each on a shape built here. The
# volume is that of the same two edges on the shape refined.
def pair_case(name, make, ends, radius, expect="pass", vol_tol=1e-3, max_tol=1e-3, bop=True):
    """The edges given by their ends, filleted together on make(): a valid
    solid of the volume the same fillet has on make() refined
    (removeSplitter), within vol_tol, no tolerance above max_tol, and
    nothing for BOP's argument check to report (bop)."""
    try:
        ref = make().removeSplitter()
        vol = ref.makeFillet(radius, [ref.Edges[edge_between(ref, a, b) - 1]
                                      for a, b in ends]).Volume
    except Exception as e:
        report(name, False, expect == "xfail",
               "EXCEPTION on the refined shape: " + str(e).strip().splitlines()[-1])
        return
    s = make()
    fillet_case(name, s, [edge_between(s, a, b) for a, b in ends], radius, expect, vol,
                max_tol=max_tol, vol_tol=vol_tol, bop=bop)


# The slotted block, its outer face (x=10) split by the spine's line below
# the floor: at (10,3,5) the slot's concave edge, the wall's edge on the
# outer face and the floor's. Two of them of opposite concavity: the corner
# between the two fillets has an edge in the outer face's plane, from the
# one fillet's line on its piece to the edge the other ends on -- an edge of
# the other piece. It was put on the first piece alone, which did not
# close. The wall's and the floor's edges together: the outer face is the
# one the two fillets share, in two pieces -- no face in common, refused.
floor = ((0, 3, 5), (10, 3, 5))
up = ((10, 3, 5), (10, 3, 14))
along = ((10, 3, 5), (10, 6, 5))
for r in (0.3, 1.0):
    pair_case("slot_split_outer_floor_and_wall_r%g" % r, lambda: slotted(outer=True),
              [floor, up], r)
    pair_case("slot_split_outer_floor_and_end_r%g" % r, lambda: slotted(outer=True),
              [floor, along], r)
    pair_case("slot_split_outer_wall_and_end_r%g" % r, lambda: slotted(outer=True),
              [up, along], r)

# The same block with the slot's wall split as well, 0.7 from the outer face:
# the floor's edge along the wall with the floor's on the outer face. That
# one's line on the outer face runs on past the vertex over the face's other
# piece, with nothing beside it on the floor: a last surface with a face on
# one side only, which the corner of one fillet removes before it starts. The
# corner of two took it for the fillet's end -- no face in common with the
# other fillet, refused ("No intersection pc pc").
corner_case("slot_split_both_floor_and_end_r0.3", slotted(wall=True, outer=True), (10, 3, 5),
            0.3, 1e-3, 1e-3, along=((-1, 0, 0), (0, 1, 0)))
# At 1 the fillet along the wall is wider than the wall's piece: it is in
# two surfaces, one for each piece of its edge, and the two fillets' lines
# meet on the floor past the split's foot, on the surface before the last.
# The corner of two is made of end surfaces; it was refused, and then made
# set back, a plate 0.11 off the refined shape's exact corner. The two
# surfaces are made one for the corner now (README.md, "A fillet in two
# surfaces at a corner of two"), and it is the refined shape's.
corner_case("slot_split_both_floor_and_end_r1", slotted(wall=True, outer=True), (10, 3, 5),
            1.0, 1e-4, 2e-4, along=((-1, 0, 0), (0, 1, 0)))


# Two fillets at a vertex, both wider than the piece of the wall between
# their edges: each ends on the piece beyond the split, and they face each
# other there, on a face the vertex is not on. As a corner of two that is
# refused; set back, the curve between their cuts was asked of the piece at
# the vertex ("a fillet ends off the face of the curve to the next"). Both
# cuts are on the far piece, and so is the curve. The refined shape's
# corner is the exact one, of two fillets on one face.
# (The box is the sweep's: a 10x10x10 box whose wall y=0 is two faces, 0.7
# of it at the corner edge x=10, each on a plane of its own -- as two
# bodies fused leave it. With the wall one plane cut in two the corner of
# two fillets is made as it stands.)
box2 = Part.read(os.path.join(HERE, "..", "draft", "sweep", "shapes",
                          "mini_mini_wall.brep"))
corner_case("box_wall_two_faces_upright_and_bottom_r1", box2, (10, 0, 0), 1.0, 0.2, 2e-3,
            along=((0, 0, 1), (-1, 0, 0)))
for tag, kw in (("wall", {"wall": True}), ("both", {"wall": True, "outer": True})):
    corner_case("slot_split_%s_top_and_upright_r1" % tag, slotted(**kw), (10, 3, 14), 1.0, 0.2,
                2e-3, along=((-1, 0, 0), (0, 0, -1)))
# The fin's wall, its piece at the block's side: the piece's top edge with
# its upright one.
corner_case("fin_on_block_wall_piece_top_and_upright_r1", fin_on_block(wall=True),
            (10, 3, 14), 1.0, 0.2, 2e-3, along=((-1, 0, 0), (0, 0, -1)))
# And the edge at the piece's foot, 0.7 long, a piece of the concave edge
# under the fin's wall, with the piece's upright edge and with the block's
# top edge: the foot's fillet in two surfaces, the lines meeting on the one
# before the last -- on the wall's far piece with the upright edge's, wider
# than the piece, and on the block's top with the top edge's. Set back
# plates, 0.03 to 0.76 off the refined shape's corner at 0.71 to 2 (the
# first with an edge 3% farther from its patch than its tolerance said, and
# so without BOP's check); the refined shape's now, the two surfaces made
# one (README.md, "A fillet in two surfaces at a corner of two"). With the
# upright edge the corner's patch differs from the refined shape's by its
# parameters, 6e-5 of volume at most, as it does at 0.3 on both.
for _r in (0.71, 0.8, 1.0, 1.5, 2.0):
    corner_case("fin_on_block_wall_piece_foot_and_upright_r%g" % _r, fin_on_block(wall=True),
                (10, 3, 5), _r, 2e-4, 2e-4, along=((-1, 0, 0), (0, 0, 1)))
for _r in (0.70001, 0.71, 0.8, 1.0, 1.5, 2.0):
    corner_case("fin_on_block_wall_piece_foot_and_top_r%g" % _r, fin_on_block(wall=True),
                (10, 3, 5), _r, 1e-5, 2e-4, along=((-1, 0, 0), (0, 1, 0)))
# #962's slots' mouths: the floor's edge along the rib, the rib's piece 0.69
# (0.79) long, with the rib's upright edge. The same corner. The mouths at
# the high-y walls of their slots are the refined shape's; their mirror
# images, these two among them, are 0.034 of volume off at most, where the
# set back plate was 0.24 off and, at y=17.1 and 1.5, refused: the patch
# between the two fillets is a filling, and differs with the parameters of
# the faces beside it. (Not with the upright edge's fillet, which was
# walked there and is the refined shape's cylinder now: README.md.)
for y in (17.1, 20.3):
    for _r in (0.8, 1.0, 1.5):
        corner_case("issue962_mouth_y%g_floor_and_upright_r%g" % (y, _r), p2, (50, y, 14), _r,
                    0.05, 2e-4, along=((-1, 0, 0), (0, 0, 1)))
# The rib's upright edge alone, first of a chain of five on a piece of the
# wall 0.69 wide, and the hex pocket's mouth edge: wider than the piece,
# they were walked, B-splines; the far piece's exact surface is taken for an
# edge of a chain too now, a cylinder as on the wall in one face.
_q2 = Part.read(os.path.join(MODELS, "issue962_pocket002.brep"))
exact_case("issue962_mouth_upright_r1_cylinder", _q2,
           edge_between(_q2, (50, 17.1, 14), (50, 17.1, 22)), 1.0, "Cylinder")
exact_case("issue962_hex_mouth_edge_r0.8_cylinder", _q2,
           edge_between(_q2, (38.8, 10.2, 24.424871), (38.8, 10.2, 19.575129)), 0.8, "Cylinder")

# #962's rib, its top corner at (38.5,10.2,32.25): the wall under the top's
# edge is in two pieces, split by the 18 long edge that comes up to the
# vertex. The top's two edges there. The fillet along the wall is a chain
# round the wall's piece and comes back to that long edge at its foot; of
# the fillet's six surfaces the corner kept the one there, at the chain's
# other end, for the one at the vertex, and removed the rest ("Failed to
# find edge", of two faces that share none). The corner was a patch, its
# edge on the wall over the two pieces (0.043 too large at 1); since
# 2ec760a1d3 (the line carried over the split to the pivot) it is the
# refined shape's, the exact corner of two fillets: the booleans either
# way leave nothing.
for r in (0.3, 1.0):
    corner_case("issue962_rib_top_corner_r%g" % r, p2, (38.5, 10.2, 32.25), r, 1e-4, 1e-4,
                along=((-1, 0, 0), (0, 1, 0)))

# The fin on the block, flush with its side: the side is an L in two faces,
# the split ending at the L's inner corner, (x,3,5). The block's top edge
# and the fin's upright edge there, on the two pieces: the two fillets had
# no face in common and the corner was a plate, inside out. Either of them
# with the concave edge between fin and block: the corner of opposite
# concavity, as on the slot.
for x in (0, 10):
    top = ((x, 3, 5), (x, 10, 5))
    inner = ((0, 3, 5), (10, 3, 5))
    upright = ((x, 3, 5), (x, 3, 14))
    for r in (0.3, 1.0):
        pair_case("fin_on_block_x%d_top_and_upright_r%g" % (x, r), fin_on_block,
                  [top, upright], r)
        pair_case("fin_on_block_x%d_top_and_inner_r%g" % (x, r), fin_on_block, [top, inner], r)
        pair_case("fin_on_block_x%d_inner_and_upright_r%g" % (x, r), fin_on_block,
                  [inner, upright], r)
# and the fin's wall split 0.7 from the side as well: at radius 1 the
# upright edge's fillet is wider than the wall's piece. It was walked, from
# the far piece -- a B-spline, which is not carried on past its end, and the
# corner was left to the plate (inside out). The fillet is the far piece's
# now, a cylinder, at an end OnSame as well (README.md).
pair_case("fin_on_block_wall_top_and_upright_r0.3", lambda: fin_on_block(wall=True),
          [((10, 3, 5), (10, 10, 5)), ((10, 3, 5), (10, 3, 14))], 0.3)
pair_case("fin_on_block_wall_top_and_upright_r1", lambda: fin_on_block(wall=True),
          [((10, 3, 5), (10, 10, 5)), ((10, 3, 5), (10, 3, 14))], 1.0, vol_tol=1e-6, max_tol=1e-5)

# The arm on the block: at (38.5,10.2,z) the arm's side meets the block's
# at 137 degrees, top and bottom in two pieces each. The upright edge with
# the block's edge or the arm's: there the corner's edge on the top (the
# bottom) crosses the split itself, and is cut in two at it, a part on each
# piece. The filling of the corner depends on the way its face's surface is
# parametrized, on the shape refined as well (its two ends, mirror images,
# differ by 4.4e-3 at radius 1): the volume within 1e-2 there.
for z, zo in ((-9.75, -3.75), (-3.75, -9.75)):
    upright = ((38.5, 10.2, z), (38.5, 10.2, zo))
    block = ((38.5, 10.2, z), (50, 10.2, z))
    arm = ((38.5, 10.2, z), (17.356, -9.425, z))
    for r, vt in ((0.3, 1e-3), (1.0, 1e-2)):
        pair_case("arm_on_block_z%g_upright_and_block_r%g" % (z, r), arm_on_block,
                  [upright, block], r, vol_tol=vt)
        pair_case("arm_on_block_z%g_upright_and_arm_r%g" % (z, r), arm_on_block,
                  [upright, arm], r, vol_tol=vt)
# The block's far corner, (50,27.2,-9.75): the bottom edge's fillet is in
# two surfaces (it ends over the split of the bottom, at the arm), and the
# corner at that end read the surfaces of the first fillet made instead of
# its own -- the upright edge's here: valid, 3.6e-3 and 0.13 too large.
for r in (0.3, 1.0):
    pair_case("arm_on_block_corner_upright_and_bottom_r%g" % r, arm_on_block,
              [((50, 27.2, -3.75), (50, 27.2, -9.75)), ((38.5, 27.2, -9.75), (50, 27.2, -9.75))],
              r)
# The arm's far end, its two top edges: the second fillet is walked (its
# line on the top crosses the split) and meets the first, a cylinder, in a
# curve that starts on the cylinder's seam; the curve's line on the cylinder
# came out a turn away there, the edge 0.9 and 2.8 off its surfaces.
for r in (0.3, 1.0):
    pair_case("arm_on_block_far_top_edges_r%g" % r, arm_on_block,
              [((17.356, -9.425, -3.75), (10.898, 16.471, -3.75)),
               ((10.898, 16.471, -3.75), (38.5, 27.2, -3.75))], r)

# The pocket's mouth again (pocket_by_split, and #962's own): its corner,
# 0.3 from the split of the front, where the mouth's two edges and the
# pocket's own inner edge meet. The fillet of the mouth's edge beside the
# split has its line on the far piece -- along the split at 0.3, inside that
# piece at 1 -- and the corner with the other fillets, made on the faces at
# the vertex, did not find it there: no face in common with the fillet of
# the mouth's other edge (a plate, inside out; at 1 that fillet ends in two
# surfaces, the last on the far piece, and the pair was refused, the vertex
# not being on the common face); with the inner edge's fillet, of opposite
# concavity, a plate whose edge on the front ends on the split or crosses
# it, left open. All three: the same plate.
def mouth_corner(tag, make, vtx, up, side, inner, big_tol, no_bop=()):
    for r in (0.3, 1.0):
        pair_case("%s_mouth_and_side_r%g" % (tag, r), make, [(vtx, up), (vtx, side)], r)
        # the corner of opposite concavity is a filling whose shape follows
        # the parameters of the face it lies against: 5e-3 from the refined
        # shape's at 1
        pair_case("%s_mouth_and_inner_r%g" % (tag, r), make, [(vtx, up), (vtx, inner)], r,
                  vol_tol=1e-2 if r == 1.0 else 1e-3)
        name = "%s_side_and_inner_r%g" % (tag, r)
        pair_case(name, make, [(vtx, side), (vtx, inner)], r,
                  vol_tol=1e-2 if r == 1.0 else 1e-3, bop=name not in no_bop)
        # all three at 1: a plate over the split here, a sphere on the
        # refined shape
        pair_case("%s_all_three_r%g" % (tag, r), make, [(vtx, up), (vtx, side), (vtx, inner)], r,
                  vol_tol=big_tol if r == 1.0 else 1e-3, max_tol=5e-3 if r == 1.0 else 1e-3)


for tag, mirror in (("", False), ("_mirror", True)):
    sg = -1 if mirror else 1
    mouth_corner("pocket_by_split%s_corner" % tag, lambda m=mirror: pocket_by_split(m),
                 (sg * 5.3, 0, 3), (sg * 5.3, 0, 7), (sg * 8, 0, 3), (sg * 5.3, 2, 3), 5e-2)
# Two of the hexagon's sixteen are not put to BOP's check: the filling of
# the top corner's side and inner edges, a three-sided patch with a point
# for its fourth side, is called self-intersecting there and is not at the
# bottom corner, its mirror image -- the same outline to the last digit, no
# fold in either (the refined shape's is passed as well). At 0.3 with clang
# and libc++ on macOS; at 1 with gcc and libstdc++ on Linux, where 0.3
# passes (2026-10-13). The patch is GeomFill_ConstrainedFilling's, made from
# the same three boundaries each time; its degrees, and with them the
# check's verdict, follow the last digits (README.md, "An edge's tolerance
# over its curves on the faces").
for tag, z, zo, zs in (("top", 24.4248711, 19.5751289, 26.8497422),
                       ("bottom", 19.5751289, 24.4248711, 17.1502578)):
    mouth_corner("issue962_hex_mouth_%s" % tag, lambda: p2.copy(), (38.8, 10.2, z),
                 (38.8, 10.2, zo), (43, 10.2, zs), (38.8, 11.7, z), 5e-2,
                 no_bop=("issue962_hex_mouth_top_side_and_inner_r0.3",
                         "issue962_hex_mouth_top_side_and_inner_r1"))

# The hexagon's side edge alone at radius 1: its fillet's line crosses the
# split 0.23 before the corner, where the pocket's next wall cuts the fillet
# already 0.58 before it -- the hexagon's 120 degrees. The fillet was cut at
# the split and walked on from there in a second surface, which the end's
# curve ran over a corner of; that end failed, and the corner setback
# fallback made it, a plate 0.025 of volume off. One exact surface now, to
# the end, as on the side in one face.
for tag, z, zs in (("top", 24.4248711, 26.8497422), ("bottom", 19.5751289, 17.1502578)):
    pair_case("issue962_hex_mouth_%s_side_r1" % tag, lambda: p2.copy(),
              [((38.8, 10.2, z), (43, 10.2, zs))], 1.0, vol_tol=1e-5, max_tol=2e-4)

# All three edges at a vertex where a split ends: the slot's corner on its
# outer face in pieces, the fin's on its block's side, the arm's on the
# block. Two of the three fillets run on the wall in two pieces, one on each
# -- no face in common, where the corner of three fillets asks for one of
# every two: a plate, inside out or 0.1 to 0.7 of volume off (tolerances to
# 2.6). The corner the wall in one face has, a torus or a filling, with its
# line on the wall in two at the split.
for r in (0.3, 1.0):
    pair_case("slot_split_outer_all_three_r%g" % r, lambda: slotted(outer=True),
              [floor, up, along], r)
    for x in (0, 10):
        pair_case("fin_on_block_x%d_all_three_r%g" % (x, r), fin_on_block,
                  [((x, 3, 5), (x, 10, 5)), ((0, 3, 5), (10, 3, 5)), ((x, 3, 5), (x, 3, 14))], r)
    # the fin's wall split as well, the upright edge's fillet walked at 1;
    # the concave edge is in two there, its piece at the corner given
    ref = fin_on_block().removeSplitter()
    vol = ref.makeFillet(r, [ref.Edges[edge_between(ref, a, b) - 1] for a, b in (
        ((10, 3, 5), (10, 10, 5)), ((0, 3, 5), (10, 3, 5)), ((10, 3, 5), (10, 3, 14)))]).Volume
    fin = fin_on_block(wall=True)
    fillet_case("fin_on_block_wall_all_three_r%g" % r, fin,
                [edge_between(fin, a, b) for a, b in (
                    ((10, 3, 5), (10, 10, 5)), ((9.3, 3, 5), (10, 3, 5)), ((10, 3, 5), (10, 3, 14)))],
                r, "pass", vol, max_tol=1e-3, vol_tol=1e-3, bop=True)
    for z, zo in ((-9.75, -3.75), (-3.75, -9.75)):
        pair_case("arm_on_block_z%g_all_three_r%g" % (z, r), arm_on_block,
                  [((38.5, 10.2, z), (38.5, 10.2, zo)), ((38.5, 10.2, z), (50, 10.2, z)),
                   ((38.5, 10.2, z), (17.356, -9.425, z))], r, vol_tol=1e-2 if r == 1.0 else 1e-3)

# #962's corner at (-15.89,5.29,-7): an edge 0.05 long and the upright edge
# below it, on the two pieces of a wall whose split ends there. Both fillets
# end on the circle's edge behind, 0.005 apart -- one runs on a plane, the
# other on a cylinder. The corner of two fillets on two pieces took them
# only at one point of that edge; a plate otherwise, inside out.
_v2 = (-15.892693841, 5.2900645058, -7.0)
for r in (0.3, 1.0):
    pair_case("issue962_short_edge_and_upright_r%g" % r, lambda: p2.copy(),
              [(_v2, (-15.8452529639, 5.2742732685, -7.0)),
               (_v2, (-15.892693841, 5.2900645058, -9.75))], r)


def pocket_mouth(undercut=True, wall=True, top=True, turn=0.0):
    """#962's pocket mouth in miniature: a block (z 0..10) with a round
    pocket (r=15.5) and a slot out of it (x 0..19.75, y 0..3, down to z=2),
    the slot's wall y=0 a radial plane. With `undercut` the pocket is z
    5..10 and widens below (r=16.75, z 2..5), else it goes down to z=2 as it
    is. The wall is split by a vertical edge at x=16.75 (`wall`; above the
    step, where the wall's outline already has a corner there) and the
    block's top by the circle r=16.75 (`top`): the two splits meet on the
    wall's top edge, 1.25 from the pocket. `turn` turns the block about z,
    degrees."""
    # (the cylinders' seams in the slot, cut away)
    seam = lambda c: c.rotated(V(0, 0, 0), V(0, 0, 1), 5.5)
    s = Part.makeBox(50, 50, 10, V(-25, -25, 0))
    if undercut:
        s = s.cut(seam(Part.makeCylinder(15.5, 5, V(0, 0, 5))))
        s = s.cut(seam(Part.makeCylinder(16.75, 3, V(0, 0, 2))))
    else:
        s = s.cut(seam(Part.makeCylinder(15.5, 8, V(0, 0, 2))))
    s = s.cut(Part.makeBox(19.75, 3, 8, V(0, 0, 2))).removeSplitter()
    tools = []
    if wall:
        tools.append(Part.LineSegment(V(16.75, 0, 5 if undercut else 2),
                                      V(16.75, 0, 10)).toShape())
    if top:
        tools.append(seam(Part.makeCircle(16.75, V(0, 0, 10))))
    if tools:
        s = s.generalFuse(tools)[0].Solids[0]
    return s.rotated(V(0, 0, 0), V(0, 0, 1), turn) if turn else s


def turned(p, turn):
    """The point `p` turned about z as pocket_mouth(turn=...) is."""
    c, sn = math.cos(math.radians(turn)), math.sin(math.radians(turn))
    return (p[0] * c - p[1] * sn, p[0] * sn + p[1] * c, p[2])


# The pocket's edge with the slot's wall, filleted wider than the wall's
# piece (1.25): the fillet's line lies on the piece beyond, along the split.
# At the top the face at end is in two pieces as well, split along a circle
# from the same foot: the cut over two pieces of the face at end took a
# straight edge between them only, and the end went to the loop over the
# faces at end, which walked the far piece's own outline, down the split
# ("Failed to find edge"); it walks the wall's now, over its pieces. Here,
# without the step, the face at the wall's foot is in one piece.
for r in (1.5, 2.0, 2.5):
    pair_case("pocket_mouth_plain_upright_r%g" % r, lambda: pocket_mouth(undercut=False),
              [((15.5, 0, 2), (15.5, 0, 10))], r, vol_tol=1e-4, max_tol=1e-5)
# With the undercut the wall's near piece ends at the step, the far one goes
# on down to the floor, and so does the fillet on the wall in one face: its
# line on the wall ends where the wall does, 3 below the edge, and the
# fillet is cut by the step, the wider pocket's wall and the floor. The
# walk, started on the far piece, stopped half the edge past its end, in
# the piece; the fillet of the two surfaces is made on the far piece now,
# and the faces at end are found along the wall's outline over its pieces.
for r in (1.5, 2.0, 2.5):
    pair_case("pocket_mouth_upright_r%g" % r, pocket_mouth,
              [((15.5, 0, 5), (15.5, 0, 10))], r, vol_tol=1e-4, max_tol=1e-5)
pair_case("pocket_mouth_wall_upright_r2", lambda: pocket_mouth(top=False),
          [((15.5, 0, 5), (15.5, 0, 10))], 2.0, vol_tol=1e-4, max_tol=1e-5)
# The step's edge with the wall, 1.25 long, at an end OnSame: the fillet's
# line on the wall's piece ends on the split, which lies on the wider
# pocket's wall -- the face at end. The line's crossing with that face is
# its very end, found the last digit past it on a block turned off the
# axes, and was taken for none ("bouchon non ecrit").
pair_case("pocket_mouth_turned_step_r1", lambda: pocket_mouth(turn=108.4),
          [(turned((15.5, 0, 5), 108.4), turned((16.75, 0, 5), 108.4))], 1.0, vol_tol=0.01,
          max_tol=1e-5)
# The model's own: edge 14 of the fillet's base (the pocket's wall above a
# cone and a ring 0.05 wide, then the wider pocket), and edges 21 and 6 of
# the chamfer's base, the same mouth without the cone
pair_case("issue962_pocket_edge_r2",
          lambda: Part.read(os.path.join(MODELS, "issue962_pocket002.brep")),
          [((-10.68613441, -11.22748999, -5.8), (-10.68613441, -11.22748999, -3.75))], 2.0,
          vol_tol=1e-4, max_tol=1e-5)
c2 = Part.read(os.path.join(HERE, "..", "draft", "sweep", "shapes", "issue962_Chamfer.brep"))
pair_case("issue962_chamfer_base_pocket_edge_r2", lambda: c2.copy(),
          [((-10.68613441, -11.22748999, -3.75), (-10.68613441, -11.22748999, -7.0))], 2.0,
          vol_tol=1e-4, max_tol=1e-5)
pair_case("issue962_chamfer_base_step_edge_r2", lambda: c2.copy(),
          [((-14.70667191, 4.895283573, -7.0), (-15.89269384, 5.290064506, -7.0))], 2.0,
          vol_tol=0.01, max_tol=1e-5)
# The same edges at the pocket's other mouth, the mirror image. There the
# fillet's cut crosses the wider pocket's circles near the end of their
# arcs, which run from 3.95 to 9.10 on the circle: the crossing came on the
# circle's first turn, at 2.81, off the edge, and the faces beside the
# edge lost it -- an invalid result of a third the volume, on the refined
# shape as well (upstream's fault).
_m5 = ((-14.70667191, 4.895283573, -5.8), (-14.70667191, 4.895283573, -3.75))
pair_case("issue962_pocket_edge_mirror_r2",
          lambda: Part.read(os.path.join(MODELS, "issue962_pocket002.brep")), [_m5], 2.0,
          vol_tol=2e-3, max_tol=1e-5)
p2r = Part.read(os.path.join(MODELS, "issue962_pocket002.brep")).removeSplitter()
fillet_case("issue962_refined_pocket_edge_mirror_r2", p2r, edge_between(p2r, *_m5), 2.0, "pass",
            11582.3197, max_tol=1e-5, vol_tol=2e-3, bop=True)
pair_case("issue962_chamfer_base_pocket_edge_mirror_r2", lambda: c2.copy(),
          [((-14.70667191, 4.895283573, -7.0), (-14.70667191, 4.895283573, -3.75))], 2.0,
          vol_tol=2e-3, max_tol=1e-5)

# The arm on the taller block, the block's side split at the arm's top:
# the edges at (38.5,10.2,-3.75) -- the upright one between arm and block
# below it, concave, and the block's own above it -- and the block's edge
# above the arm at (38.5,27.2,-3.75). Each ends at a vertex of four sharp
# edges, its side on the block's face stopped on the split: an edge of the
# vertex, lying in the plane of the arm's top. The loop over the faces at
# end took every face round the vertex, found the fillet short of the edge
# between the arm's top and the block's wall, and left the end to a plate:
# valid, with tolerances of 3e-3 to 7e-2, volumes off by up to 0.3, and
# BOP's check failing on the first from 0.8 on. The arm's top alone is cut
# now, as on the side in one face (README.md).
_near = lambda: arm_on_tall_block(split=False, near=True)
for r in (0.3, 0.8, 2.0):
    pair_case("arm_on_tall_block_near_split_down_r%g" % r, _near,
              [((38.5, 10.2, -3.75), (38.5, 10.2, -9.75))], r, vol_tol=1e-5, max_tol=2e-4)
    pair_case("arm_on_tall_block_near_split_up_r%g" % r, _near,
              [((38.5, 10.2, -3.75), (38.5, 10.2, 14))], r, vol_tol=1e-5, max_tol=2e-4)
    pair_case("arm_on_tall_block_far_split_up_r%g" % r, arm_on_tall_block,
              [((38.5, 27.2, -3.75), (38.5, 27.2, 14))], r, vol_tol=1e-5, max_tol=2e-4)
# the model's own: edges 49, 50 and 56 of the fillet's base
_p2 = lambda: Part.read(os.path.join(MODELS, "issue962_pocket002.brep"))
pair_case("issue962_arm_upright_r0.8", _p2, [((38.5, 10.2, -3.75), (38.5, 10.2, -9.75))], 0.8,
          vol_tol=1e-4, max_tol=2e-4)
pair_case("issue962_block_edge_over_arm_r2", _p2, [((38.5, 10.2, -3.75), (38.5, 10.2, 14))],
          2.0, vol_tol=1e-4, max_tol=2e-4)
pair_case("issue962_block_far_edge_over_arm_r2", _p2,
          [((38.5, 27.2, -3.75), (38.5, 27.2, 14))], 2.0, vol_tol=1e-4, max_tol=2e-4)

# An arch on a plate (#309): a half cylinder of radius R standing on a plate
# as long as its diameter, so that the plate's ends are tangent to it. The
# edge at the arch's foot, between its end face and the plate's top, ends
# where the cylinder, tangent to the plate's end, comes down to the top.
# The fillet's end is cut by the cylinder, which grows over it down to the
# plate's top edge -- an edge that lies on the cylinder and is none of its
# face. The end point's parameters on the cylinder were read off that
# edge's curve on the face, and left as they stood when it has none, at
# (0,0): upstream's fault, on the body in one piece. "Valid", with a vertex
# at a tolerance of 21 (71 and 210 at R=50), a volume of 671 for 797, and
# BOP's check failing. And with the plate's ends split under the arch's
# end face, as #309 has them, the cylinder and the end's two pieces were
# taken for three tangent faces, and the fillet cut by the end's plane
# instead: invalid.
def arch_on_plate(split=False, R=10.0):
    plate = Part.makeBox(12, 2 * R, 2, V(-10, -R, -2))
    cyl = Part.makeCylinder(R, 2, V(0, 0, 0), V(1, 0, 0)).common(
        Part.makeBox(2, 2 * R, R, V(0, -R, 0)))
    s = plate.fuse(cyl).removeSplitter()
    if split:
        s = s.generalFuse([Part.LineSegment(V(0, y, -2), V(0, y, 0)).toShape()
                           for y in (-R, R)])[0].Solids[0]
    return s


for r, vol in ((0.3, 794.545534), (0.8, 796.905452), (2.0, 811.298183)):
    aop = arch_on_plate()
    fillet_case("arch_on_plate_foot_r%g" % r, aop, edge_between(aop, (0, -10, 0), (0, 10, 0)), r,
                "pass", vol, 1e-5, vol_tol=1e-4, bop=True)
    pair_case("arch_on_plate_split_foot_r%g" % r, lambda: arch_on_plate(split=True),
              [((0, -10, 0), (0, 10, 0))], r, vol_tol=1e-5, max_tol=1e-5)
# the model's own, edge 9, in pieces and refined
s309 = Part.read(os.path.join(HERE, "..", "draft", "sweep", "shapes", "issue309_shape.brep"))
s309r = s309.removeSplitter()
for r, vol in ((0.3, 12765.2985), (0.8, 12777.1032), (2.0, 12849.1968)):
    pair_case("issue309_arch_foot_r%g" % r, lambda: s309.copy(), [((0, -50, 0), (0, 50, 0))], r,
              vol_tol=1e-3, max_tol=2e-4)
    fillet_case("issue309_refined_arch_foot_r%g" % r, s309r,
                edge_between(s309r, (0, -50, 0), (0, 50, 0)), r, "pass", vol, 2e-4, vol_tol=1e-3,
                bop=True)

# #474's Fillet002 input, edge 13: an upright edge of the block under the
# ramp, 11 long. Its wall is in two pieces, split at the level where the
# ramp starts, and the ramp rises from there along the other face: that
# face's line runs on 0.027 past the split's level to the ramp's edge. Two
# surfaces, the second past the vertex; the corner took the split for a
# tangent edge and made a plate -- tolerance 0.05, BOP's check failing, the
# volume 0.035 off at 0.8. On the wall in one face the two are one surface
# and the fillet is cut by the ramp.
_p474 = lambda: Part.read(os.path.join(MODELS, "issue474_fillet002_base.brep"))
for r in (0.3, 0.8):
    pair_case("issue474_f002_wall_edge_r%g" % r, _p474,
              [((-3.803564356, 8.156770083, 11.0), (-3.803564356, 8.156770083, 0.0))], r,
              vol_tol=1e-4, max_tol=2e-4)

# The arm on the block, both as tall: their tops (and bottoms) are one
# plane in two faces, split along x=38.5. At (38.5,27.2) the block's top
# edge along y=27.2 with the upright edge between arm and block: the top
# edge's fillet has its line on the top stopped on the split, 0.77 short of
# the arm's top edge, which the upright edge's fillet ends on -- the pivot
# both end on when the top is one face, where the two are cut by one
# another. "Fillets are not on the same arc": a plate, tolerances of 3.6e-3
# and 1.2e-2, the volume 0.074 off at radius 1. The line is carried over
# the split to the pivot now (README.md).
for z, zo in ((-9.75, -3.75), (-3.75, -9.75)):
    for r in (0.3, 1.0):
        pair_case("arm_on_block_far_z%g_upright_and_block_r%g" % (z, r), arm_on_block,
                  [((38.5, 27.2, z), (38.5, 27.2, zo)), ((38.5, 27.2, z), (50, 27.2, z))], r,
                  vol_tol=1e-5, max_tol=2e-4)

# The pocket's mouth on #962: the wall's edge with the circle of the cone
# below it, radius 1. The two fillets are cut by one another along a curve
# whose ends are put on the points known on each of them, and the curve is
# farthest off the wall's fillet a little inside its end: 2.51e-6 at 0.003
# of it for 2.18e-6 at the end. The edge's tolerance, the largest distance
# at the samples and a twentieth more, did not cover that, and BOP's check
# called the curve invalid -- on the block in pieces; on the refined one
# the same margin held by chance (7.32e-6 for 7.63e-6). The edges the
# fillet makes cover their curves on the faces now (README.md).
pair_case("issue962_pocket_wall_and_cone_r1",
          lambda: Part.read(os.path.join(MODELS, "issue962_pocket002.brep")),
          [((-10.68613441, -11.22748999, -5.8), (-14.70667191, 4.895283573, -5.8)),
           ((-10.68613441, -11.22748999, -5.8), (-10.68613441, -11.22748999, -3.75))], 1.0,
          vol_tol=2e-3, max_tol=1e-4)

# The rib's top corners on #962: the top with the rib's slope and with the
# wall beside it, at (38.5,13.7,32.25) and its twin at y=17.1. The wall is
# in two pieces, split 0.46 from the corner, and the split's foot is on the
# slope's edge with the wall: that edge, the pivot both fillets end on, is
# in two pieces itself, the first 0.52 long and dropping 0.24. The wall's
# fillet has its line 0.3 below the top (and more): under the first piece's
# end, across the split, to the second piece. It ended where the fillet's
# edge does, in the wall's face, with no edge to end on -- a plate, 3.7e-3
# of tolerance and 0.003 of volume off at radius 0.3, 0.1 at 1. The line is
# carried over the split to the pivot's second piece, and the two pieces
# are one pivot (README.md).
for nm, y, yo in (("near", 13.7, 10.2), ("far", 17.1, 20.3)):
    for r in (0.3, 0.8, 1.0):
        pair_case("issue962_rib_top_%s_r%g" % (nm, r),
                  lambda: Part.read(os.path.join(MODELS, "issue962_pocket002.brep")),
                  [((38.5, y, 32.25), (38.5, yo, 32.25)), ((38.5, y, 32.25), (35.5, y, 32.25))],
                  r, vol_tol=1e-4, max_tol=2e-4)

# An edge its two vertices cover (README.md, "An edge of no length"). #474's
# Fillet003 input keeps a face 1.4e-7 wide beside the hexagon's corner at
# (6.415,11.307), between two edges on one line, and one like it at
# (4.441,7.828): a fillet ending at either crossed the face with an edge of
# that length -- the hexagon's bottom edge (53) and the thread's two helices
# (13 at radius 9, 5 at radius 13). On #876 the post is flush with the
# plate's round end and drafted by a degree: the edge at its foot is a
# degree from smooth, and its fillet, a few thousandths wide, ends in an
# edge 1.1e-6 (10) and 5.1e-5 (42, 53) long. Valid each time, and refused by
# BOP's check: "too small edge", "self-intersecting vertex".
# (The tolerances asked are the results' own, away from that end: 0.018 on
# the outer helix, 2e-4 along #876's edge 10. Edges 42 and 53
# at 2 are not cases: their corners come out loose with one compiler or
# another -- 42 with gcc on Linux (0.02, 0.24 of volume less), 53 with MSVC
# (0.0115, 0.19 less), each fine with the other two -- a fillet a degree
# from smooth at radius 2 is that sensitive.)
for e, r, vol, tol in ((53, 0.3, 1988.8326, 1e-3), (13, 0.3, 1985.1153, 1e-3),
                       (5, 0.3, 1983.6314, 0.02)):
    fillet_case("issue474_f003_no_width_e%d_r%g" % (e, r),
                Part.read(os.path.join(MODELS, "issue474_fillet003_base.brep")),
                e, r, "pass", vol, tol, vol_tol=1e-3, bop=True)
for e, r, vol, tol in ((10, 0.3, 8665.7839, 1e-3),):
    fillet_case("issue876_post_foot_e%d_r%g" % (e, r),
                Part.read(os.path.join(MODELS, "issue876_fillet_base.brep")),
                e, r, "pass", vol, tol, vol_tol=1e-3, bop=True)
# #876's post stands flush with the plate's sides, its walls drafted a
# degree: at 0.3 a fillet of its foot is 0.005 wide all along -- edge 52
# between two planes, 50 and 58 between a corner's cylinder and cone. Narrower than 100 times the approximation
# tolerance, it was searched for a section closing to a point, and split at
# each minimum of its width -- found by the derivative alone, of no depth
# here -- its section there one vertex as loose as the section is long
# (0.00524), its two lines both through it: BOP's check, "self-intersecting
# edge". They came out with two, five and four faces more than now: one
# fillet face, its edges at 3e-4 at most.
for e, vol in ((52, 8665.7839), (50, 8665.7841), (58, 8665.7841)):
    fillet_case("issue876_kink_e%d_r0.3" % e,
                Part.read(os.path.join(MODELS, "issue876_fillet_base.brep")),
                e, 0.3, "pass", vol, 1e-3, vol_tol=1e-3, bop=True)
# #273's handle stands on the cylinder's wall two degrees from it: a fillet
# down either of its front edges ends at the handle's foot in an edge
# 1.5e-5 long, closed on one vertex. The input has a vertex at 0.03.
for e, vol in ((12, 8559.3314), (14, 8559.3365)):
    fillet_case("issue273_handle_foot_e%d_r0.3" % e,
                Part.read(os.path.join(HERE, "..", "draft", "sweep", "shapes",
                                       "issue273_Fillet.brep")),
                e, 0.3, "pass", vol, 0.031, vol_tol=1e-3, bop=True)
# The fillet down edge 5 ended in a corner whose vertex ShapeFix raised to
# 0.029 to meet the circle beside it; the circle's edge, at 1e-7, had to
# cover it too (README.md, "Corner plates held to their own miss"). That
# corner ran on past the vertex and is refused now, the corner set back
# (README.md, "A fillet run on past its vertex"): 8559.4849, within the
# 0.02 kept for the compiler (8559.4856 with MSVC before). No max_tol: the
# loose-end check would allow the input's vertex of 0.03.
p273f = Part.read(os.path.join(HERE, "..", "draft", "sweep", "shapes", "issue273_Fillet.brep"))
fillet_case("issue273_corner_circle_end_e5_r0.3", p273f, 5, 0.3, "pass", 8559.4933, vol_tol=0.02)
# #273's rim arcs and #474's step edges, between faces 1.5 deg apart: the
# fillet's free side ran on past the vertex as far as the spine was
# extended, the corner cut along the strip (BOP's check: edges and faces
# crossing themselves; #474's invalid). Refused at the end, and set back.
for e, r, vol in ((5, 2, 8559.4279), (7, 2, 8559.4286)):
    fillet_case("issue273_rim_run_on_e%d_r%g" % (e, r), p273f, e, r, "pass", vol,
                vol_tol=1e-3, bop=True)
p474f3 = Part.read(os.path.join(HERE, "..", "draft", "sweep", "shapes", "issue474_Fillet003.brep"))
for e, r, vol in ((2, 0.3, 1988.8707), (18, 0.8, 1988.8386)):
    fillet_case("issue474_f003_run_on_e%d_r%g" % (e, r), p474f3, e, r, "pass", vol, 1e-3,
                vol_tol=1e-3, bop=True)
# #273's handle on the cup's top: its sides' feet (E11, E15), each a concave
# fillet ending where the handle's front and back stand on the cup's rim and
# carry its wall on. The piece of the rim from the vertex to the fillet's
# end came out the wrong way round in both its faces (invalid, as upstream).
# The result is the input fused with the strip between the faces and the
# fillet's cylinder, cut to the cone the handle's ends lie on: BOP's
# difference both ways is empty; the volumes are those made, held to 1e-3
# (the faces' integration differs by more from the plain to the adaptive).
# Each on a copy of its own: at 2 the fillet raises the tolerance of the
# rim's vertex, which its input shares with the result (as upstream), and
# every later case on the same input would carry it.
for e, r, vol, tol in ((11, 0.3, 8560.0641, 0.031), (11, 0.8, 8563.6287, 0.031),
                       (11, 2, 8585.0031, 0.19), (15, 0.3, 8560.0709, 0.031),
                       (15, 0.8, 8563.6332, 0.031), (15, 2, 8585.2381, 0.19)):
    fillet_case("issue273_handle_foot_e%d_r%g" % (e, r), p273f.copy(), e, r, "pass", vol,
                tol, vol_tol=1e-3, bop=True)
# #273's pocket in the handle's top, its rims (E23, E24; E22 the base): the
# fillet's end at the pocket's apex of 22 deg is a cap in the other wall,
# as upstream's at 0.3; from 0.49 the cap runs off the top, and the cut is
# carried on into the handle's end (README.md, "A cut that runs off the
# face"). Refused before, and a folded patch set back before that. Each
# single rim's volume is that of the strip cut away by booleans, within
# 5e-4: 8559.0377 at 0.5, 8558.3169 at 0.8, 8557.8240 at 0.95.
fillet_case("issue273_pocket_apex_cap_e23_r0.3", p273f, 23, 0.3, "pass", 8559.3262, 0.031,
            vol_tol=1e-3, bop=True)
for e in (23, 24):
    fillet_case("issue273_pocket_apex_off_e%d_r0.8" % e, p273f, e, 0.8, "pass", 8558.3169, 0.031,
                vol_tol=1e-3, bop=True)
for r, vol in ((0.5, 8559.0377), (0.95, 8557.8240)):
    fillet_case("issue273_pocket_apex_off_e23_r%g" % r, p273f, 23, r, "pass", vol, 0.031,
                vol_tol=1e-3, bop=True)
fillet_case("issue273_pocket_apex_off_e22_e23_r0.8", p273f, [22, 23], 0.8, "pass", 8557.8386,
            0.031, vol_tol=1e-3, bop=True)
fillet_case("issue273_pocket_apex_off_e22_e24_r0.6", p273f, [22, 24], 0.6, "pass", 8558.5757,
            0.031, vol_tol=1e-3, bop=True)
# The chamfer's end there the same corner: the triangle cut away by booleans
# to the digit shown.
for e, r, vol in ((23, 0.5, 8558.4246), (23, 0.8, 8556.6985), (24, 0.8, 8556.6985),
                  (23, 0.95, 8555.5202)):
    fillet_case("issue273_pocket_apex_off_chamfer_e%d_r%g" % (e, r), p273f, e, r, "pass", vol,
                0.031, chamfer=True, vol_tol=1e-4, bop=True)
fillet_case("issue273_pocket_apex_off_chamfer_e22_e23_r0.8", p273f, [22, 23], 0.8, "pass",
            8555.5159, 0.031, chamfer=True, vol_tol=1e-4, bop=True)
# The same ends flat (ChFi3d_Builder::SetFlatEndAtVertex, ../flat_end.py;
# FreeCAD's Fillet features from their version 1): the cap in the other wall
# would cut into the top past the apex, and at the base corners (79 deg) into
# the floor's wall past them, so the fillet ends at each in a flat face square
# to the rim, nothing past the pocket cut. Each single rim's volume is that of
# the strip from the apex to the base corner cut away by booleans, to the
# digit shown; 0.487 is refused without the flat end (README.md).
for e, r, vol in ((23, 0.1, 8559.4677), (23, 0.3, 8559.3297), (23, 0.487, 8559.0759),
                  (23, 0.8, 8558.3813), (24, 0.8, 8558.3813), (23, 0.95, 8557.9287)):
    fillet_case("issue273_pocket_flat_e%d_r%g" % (e, r), p273f, e, r, "pass", vol, 0.031,
                vol_tol=1e-4, bop=True, flat=True)
# with the base: its own end at the other base corner flat too; both rims:
# where two rims meet at an acute corner -- the apex, a base corner -- the
# corner's upright edge is filleted too, the three making the corner in it
# (README.md, "Both rims: the tip filleted"); the two alone met past it
# (8557.9030 and 8557.2101 before), the other ends flat
fillet_case("issue273_pocket_flat_e22_e23_r0.8", p273f, [22, 23], 0.8, "pass", 8558.2038,
            0.031, vol_tol=1e-3, bop=True, flat=True)
fillet_case("issue273_pocket_flat_e23_e24_r0.8", p273f, [23, 24], 0.8, "pass", 8560.4721,
            0.031, vol_tol=1e-3, bop=True, flat=True)
fillet_case("issue273_pocket_flat_e23_e24_r0.3", p273f, [23, 24], 0.3, "pass", 8559.5564,
            0.031, vol_tol=1e-3, bop=True, flat=True)
# the same with the upright asked for too: the same result
fillet_case("issue273_pocket_flat_e23_e24_e30_r0.8", p273f, [23, 24, 30], 0.8, "pass",
            8560.4721, 0.031, vol_tol=1e-3, bop=True, flat=True)
# without the flat end, as before: the two meet past the apex
fillet_case("issue273_pocket_both_rims_e23_e24_r0.8", p273f, [23, 24], 0.8, "pass", 8557.2006,
            0.031, vol_tol=1e-3, flat=False)


# A rectangular pocket's corner, both rims at it, the flat end on: a right
# angle is no narrow tip, and its upright is not filleted -- as without.
def _rect_pocket_rims():
    s = Part.makeBox(30, 30, 10).cut(Part.makeBox(10, 10, 1, V(10, 10, 9))).removeSplitter()
    c = V(20, 20, 10)
    return s, [i + 1 for i, e in enumerate(s.Edges)
               if any(v.Point.distanceToPoint(c) < 1e-9 for v in e.Vertexes)
               and abs(e.Vertexes[0].Point.z - e.Vertexes[-1].Point.z) < 1e-9]


_rp, _rims = _rect_pocket_rims()
fillet_case("pocket_rect_corner_flat_rims_r0.3", _rp, _rims, 0.3, "pass", 8899.6111,
            vol_tol=1e-3, bop=True, flat=True)


# V pockets too narrow for the tip's edge at the rims' radius: filleted at 0.8
# a 10 deg tip fills 8.4 back, past its walls' 8, and the two rims met 5.6
# past the apex without it; the edge is filleted at half the radius now (a
# quarter, an eighth, where half is not made). At 10 deg 3 deep, 1.5, the two
# alone were refused by BOP's check
def _v_pocket_rims(deg, depth):
    h = math.radians(deg / 2.0)
    pts = [(15 - 8 * math.tan(h), 8), (15 + 8 * math.tan(h), 8), (15, 16)]
    w = Part.makePolygon([App.Vector(x, y, 10) for x, y in pts]
                         + [App.Vector(pts[0][0], pts[0][1], 10)])
    s = Part.makeBox(30, 30, 10).cut(
        Part.Face(w).extrude(App.Vector(0, 0, -depth))).removeSplitter()
    c = App.Vector(15, 16, 10)
    return s, [i + 1 for i, e in enumerate(s.Edges)
               if any(v.Point.distanceToPoint(c) < 1e-9 for v in e.Vertexes)
               and abs(e.Vertexes[0].Point.z - e.Vertexes[-1].Point.z) < 1e-9]


for deg, depth, r, vol in ((10, 1, 0.8, 8994.8063), (10, 3, 1.5, 8982.7652),
                           (22, 3, 2.5, 8969.0308)):
    _vp, _vrims = _v_pocket_rims(deg, depth)
    fillet_case("pocket_v%d_d%g_flat_tip_rims_r%g" % (deg, depth, r), _vp, _vrims, r, "pass",
                vol, vol_tol=1e-3, bop=True, flat=True)

# #631: a loft on a pad, the fillet of their joint (concave, under the loft's
# overhang) ending on the pad's side and the loft's -- a plane, as a loft
# makes it, a B-spline of 2 x 2 poles. Its cut on the loft's side lies past
# the B-spline's bounds, where a plane runs on; bounded, it was not found
# and the end was a plate bulging out of the pad's side from 4 on (the
# report: "wrong but valid, radius > 3"), 85 over at 15, the fillet itself
# 118. Now the face is extended for the cut: the volume is the one of the
# loft rebuilt with its faces planes, to 1e-4, at every radius.
p631l = Part.read(os.path.join(MODELS, "issue631_loft_joint.brep"))
e631l = edge_between(p631l, (4.022164, -10, 16.501574), (-18.88777, -10, 16.501574))
for r, vol in ((1, 9801.8039), (4, 9809.7324), (10, 9853.978), (15, 9919.5607)):
    fillet_case("issue631_loft_joint_e18_r%g" % r, p631l, e631l, r, "pass", vol, vol_tol=1e-3,
                bop=True)
# the chamfer's: the triangle from the apex to the base corner
for r, vol in ((0.5, 8558.4805), (0.8, 8556.9137)):
    fillet_case("issue273_pocket_flat_chamfer_e23_r%g" % r, p273f, 23, r, "pass", vol, 0.031,
                chamfer=True, vol_tol=1e-4, bop=True, flat=True)
# as wide as the wall: the pocket is 1 deep, the fillet would take the whole
# wall and meet the floor at its edge -- refused, flat end or not (README.md)
fillet_case("issue273_pocket_wall_wide_e23_r1", p273f, 23, 1.0, "xfail", flat=True)
_part_params = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Part")
_had_fallback = "FilletCornerSetbackFallback" in _part_params.GetFloats()
_fallback = _part_params.GetFloat("FilletCornerSetbackFallback", 2.0)
_part_params.SetFloat("FilletCornerSetbackFallback", 0.0)
try:
    refused_case("issue273_rim_run_on_e5_r0.3_no_fallback", p273f, 5, 0.3)
finally:
    if _had_fallback:
        _part_params.SetFloat("FilletCornerSetbackFallback", _fallback)
    else:
        _part_params.RemFloat("FilletCornerSetbackFallback")
# #273's Fillet001: the rim beside the handle (E9, a quarter of the circle in
# one spine with E3) at 1, the radius of the fillet the input already has on
# the rim's other half. The new fillet's line on the wall lies on that one's
# lower edge (E4, the same circle at z 17); its end was taken where the line
# runs onto that edge, at its vertex across the handle, 5.2 off: the rim alone
# 0.07 too deep under the handle's face, with the handle's corner edge E22 a
# corner plate of negative area (invalid), with its foot E16 refused. The
# fillet ends at the handle now, the mirror of the input's own. No bop: the
# input fails BOP's check itself (its vertices at 0.7).
p273f1 = Part.read(os.path.join(HERE, "sweep", "shapes", "issue273_Fillet001.brep"))
for es, vol in (([9], 8525.7820), ([9, 22], 8524.0432), ([9, 16], 8532.5212)):
    fillet_case("issue273_f001_rim_onto_edge_%s_r1" % "_".join("e%d" % e for e in es), p273f1,
                es, 1.0, "pass", vol, vol_tol=1e-3)
# #876's top split along a rounded rectangle, two of its corner arcs (r 0.69;
# Fillet's 85 and 87, Fillet001's 123 and 125): splits between two coplanar planes, numbered past
# 2 pi. The tangency test sampled the periodic pcurves outside their first
# period, every sample refused, and called them edges: the chamfer built an
# invalid result -- at 0.3 on 87 and 125 a crash, the topological build's
# repair removing edges under its own iterator (3a0593e01f). Refused now,
# the edge tangent (ce3b4bff39); before 3a0593e01f the suite died here.
for nm, path, es in (("fillet", ("..", "draft", "sweep", "shapes", "issue876_Fillet.brep"),
                      (85, 87)),
                     ("fillet001", ("sweep", "shapes", "issue876_Fillet001.brep"), (123, 125))):
    for e in es:
        for r in (0.3, 0.8):
            refused_case("issue876_%s_chamfer_flat_split_e%d_r%g" % (nm, e, r),
                         Part.read(os.path.join(HERE, *path)), e, r, chamfer=True)
# #631's corners of two fillets: a plate approximated to ten times its miss
# of its boundary left a corner loose enough to swallow a short side --
# under it an edge too small, its vertices overlapping, in BOP's check.
p631f = Part.read(os.path.join(HERE, "..", "draft", "sweep", "shapes", "issue631_Fillet.brep"))
for es, vol, tol in (([9, 21], 41870.6264, 1e-3), ([1, 8], 41865.7269, 0.02),
                     ([15, 16], 41870.0851, 0.02)):
    fillet_case("issue631_corner_plate_e%s_r0.3" % "_".join(map(str, es)), p631f, es, 0.3,
                "pass", vol, tol, vol_tol=1e-3, bop=True)

# #523's box and cylinder, the bottom: the cylinder's rim and one of the
# box's two edges it ends on, at radius 1. The rim's fillet touches the
# bottom on a whole circle of radius 1, the edge's on a line tangent to it:
# the bottom is a rectangle and a disc meeting at a point, where the circle
# ran from one new vertex to another at the same place (README.md, "A
# pinch between two new vertices").
for nm, pair in (("a", [8, 13]), ("b", [9, 11]), ("c", [11, 14]), ("d", [13, 15])):
    fillet_case("issue523_bottom_rim_and_edge_%s_r1" % nm,
                Part.read(os.path.join(MODELS, "issue523_box_cylinder.brep")),
                pair, 1.0, "pass", 1090.6315, 2e-3, vol_tol=1e-3, bop=True)

# #474's first fillet input, the corner at (-13,1.992,-0.176): three planes,
# two of them five degrees off square, and the two edges on the third
# filleted. Two cylinders and their mitre, an exact quarter of an ellipse
# with the range -PI/2..0 -- on which BOP found no projection of a point,
# so that it took the mitre for a new section and the two fillets for
# self-intersecting (README.md, "The roots of a trigonometric equation
# below zero").
for r, vol in ((0.3, 1886.6776), (1.0, 1883.8419)):
    fillet_case("issue474_skew_corner_r%g" % r,
                Part.read(os.path.join(HERE, "..", "draft", "sweep", "shapes",
                                       "issue474_Fillet.brep")),
                [19, 21], r, "pass", vol, 1e-5, vol_tol=1e-3, bop=True)

# A cylinder boss standing flush with a plate's side: its foot circle is
# tangent to the plate's top edge, and the top narrows to nothing there. The
# fillet round the foot opens at the tangent point, each end cut by the
# side carried up, which grows over the gap (README.md, "A boss flush with
# the plate's side"); it was refused at every radius ("TopOpeBRepDS_
# DataStructure::Point", a point of index 0). The result is the fillet made
# on a plate reaching past the side, cut by the side's plane: boss_flush_csg
# makes both and takes one from the other. The boss set in from the side is
# made as it always was.
def _boss(y, turn=0.0, plate=None, x=15.0):
    b = Part.makeCylinder(5, 10, App.Vector(0, 0, 3))
    b.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), turn)
    b.translate(App.Vector(x, y, 0))
    return (plate if plate is not None else Part.makeBox(30, 20, 3)).fuse(b).removeSplitter()


def _foot(s, z=3.0):
    return [i for i, e in enumerate(s.Edges, 1)
            if e.Curve.__class__.__name__ == "Circle" and e.Curve.Radius < 5.5
            and abs(e.BoundBox.ZMin - z) < 1e-7 and abs(e.BoundBox.ZMax - z) < 1e-7]


def _rim(turn):
    p = Part.makeCylinder(20, 3)
    p.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), turn)
    return p


_flush = _boss(5)
for r, vol in ((0.3, 2585.9842), (1.0, 2591.8420), (2.0, 2611.2741), (4.5, 2720.7921)):
    fillet_case("boss_flush_foot_r%g" % r, _flush, _foot(_flush), r, "pass", vol, 1e-5,
                vol_tol=1e-3, bop=True)
# the boss's seam on the far side: one edge of the foot, both ends on it
_turned = _boss(5, 180.0)
fillet_case("boss_flush_turned_foot_r1", _turned, _foot(_turned), 1.0, "pass", 2591.8420, 1e-5,
            vol_tol=1e-3, bop=True)
# two bosses on one side; the foot and the boss's top together
_two = _boss(5, plate=_boss(5, plate=Part.makeBox(40, 20, 3), x=10.0), x=28.0)
fillet_case("boss_flush_two_feet_r1", _two, _foot(_two), 1.0, "pass", 3983.6841, 1e-5,
            vol_tol=1e-3, bop=True)
fillet_case("boss_flush_foot_and_top_r1", _flush, _foot(_flush) + _foot(_flush, 13.0), 1.0,
            "pass", 2585.4013, 1e-5, vol_tol=1e-3, bop=True)
# a round plate, the boss against its rim from inside: the side a cylinder
_inrim = _boss(0, 90.0, _rim(90.0))
for r, vol in ((0.3, 4555.8909), (1.0, 4561.6566), (2.0, 4580.5973)):
    fillet_case("boss_rim_foot_r%g" % r, _inrim, _foot(_inrim), r, "pass", vol, 1e-5,
                vol_tol=1e-3, bop=True)


def boss_flush_csg(name, r):
    """The flush boss's fillet against the fillet on a plate reaching past
    the side, cut there: nothing of either outside the other."""
    try:
        f = _flush.makeFillet(r, [_flush.Edges[i - 1] for i in _foot(_flush)])
        wide = _boss(5, plate=Part.makeBox(30, 40, 3, App.Vector(0, -20, 0)))
        ref = wide.makeFillet(r, [wide.Edges[i - 1] for i in _foot(wide)]).common(
            Part.makeBox(100, 100, 100, App.Vector(-20, 0, -20)))
        a, b = f.cut(ref).Volume, ref.cut(f).Volume
        ok = f.isValid() and a < 1e-6 and b < 1e-6 and abs(f.Volume - ref.Volume) < 1e-3
        report(name, ok, False, "vol=%.4f ref=%.4f out=%.1e,%.1e" % (f.Volume, ref.Volume, a, b))
    except Exception as e:
        report(name, False, False, "EXCEPTION " + str(e).strip().splitlines()[-1])


boss_flush_csg("boss_flush_csg_r1", 1.0)
boss_flush_csg("boss_flush_csg_r2", 2.0)
# Still refused, as they were: a chamfer (its cut reaches the line on the
# boss tangent to it, a corner of no angle); the rim's seam through the
# tangent point (the seam would have to run on up); the boss at a corner of
# the plate, flush with two sides.
fillet_case("boss_flush_chamfer_r1", _flush, _foot(_flush), 1.0, "xfail", chamfer=True)


# A drafted boss (a cone, radius 5 to 4) flush at its foot: it touches the
# side only there, and the fillet's line on it never reaches the side. The
# fillet made on a plate reaching past the side and cut by it is one ring,
# its lower edge notched by the side's cut below that line; the gap between
# the fillet's two ends is closed by its surface run on (README.md, "A
# drafted boss flush with the plate's side"). Refused before
# ("TopOpeBRepDS_DataStructure::Point"). Each is checked against that
# construction: valid, BOP's check, no tolerance above 1e-4, within 1e-3 of
# its volume, nothing of either outside the other.
def _cone(x, y, turn=0.0, r2=4.0):
    c = Part.makeCone(5, r2, 10, App.Vector(0, 0, 3))
    c.rotate(App.Vector(0, 0, 0), App.Vector(0, 0, 1), turn)
    c.translate(App.Vector(x, y, 0))
    return c


def drafted_csg(name, shape, wide, keep, r, edges=None, chamfer=False, vol_tol=1e-3):
    """The fillet (chamfer) of the feet of <shape> against the same on
    <wide>, the plate reaching past the side, in common with <keep>."""
    try:
        def op(s, es):
            es = [s.Edges[i - 1] for i in es]
            return s.makeChamfer(r, es) if chamfer else s.makeFillet(r, es)
        f = op(shape, edges[0] if edges else _foot(shape))
        ref = op(wide, edges[1] if edges else _foot(wide)).common(keep)
        problems = []
        if not f.isValid():
            problems.append("invalid")
        else:
            problems += [p for p in [ends_problem(f, widest(shape))] if p]
            tol = max([e.Tolerance for e in f.Edges] + [v.Tolerance for v in f.Vertexes])
            if tol > 1e-4:
                problems.append("tolerance %.3g" % tol)
            if abs(f.Volume - ref.Volume) > vol_tol:
                problems.append("volume %.5f != %.5f" % (f.Volume, ref.Volume))
            a, b = f.cut(ref).Volume, ref.cut(f).Volume
            if a > 1e-6 or b > 1e-6:
                problems.append("out %.1e,%.1e" % (a, b))
            try:
                f.check(True)
            except Exception as e:
                problems.append("bop: " + " ".join(str(e).split())[:60])
        report(name, not problems, False,
               "; ".join(problems) if problems else "vol=%.4f ref=%.4f" % (f.Volume, ref.Volume))
    except Exception as e:
        report(name, False, False, "EXCEPTION " + str(e).strip().splitlines()[-1])


_half = Part.makeBox(100, 100, 100, App.Vector(-20, 0, -20))
_plate = lambda: Part.makeBox(30, 20, 3)
_wide = lambda: Part.makeBox(30, 40, 3, App.Vector(0, -20, 0))
_drafted = _plate().fuse(_cone(15, 5)).removeSplitter()
_drafted_wide = _wide().fuse(_cone(15, 5)).removeSplitter()
for r in (0.3, 1.0, 2.0, 4.0):
    drafted_csg("boss_drafted_flush_foot_r%g" % r, _drafted, _drafted_wide, _half, r)
# drafted 0.6 deg and 11 deg. Near flush the cut climbs to just under the
# line on the boss, and the volume's integration over it moves by some
# 1e-3 with the cut's parameters (0.0029, 0.0038 at 41 and 81 points),
# where the bump it bounds on the side agrees to 8e-6 (at radius 3).
for r2, vt in ((4.9, 0.01), (3.0, 1e-3)):
    _d = _plate().fuse(_cone(15, 5, r2=r2)).removeSplitter()
    _dw = _wide().fuse(_cone(15, 5, r2=r2)).removeSplitter()
    drafted_csg("boss_drafted%g_flush_foot_r1" % r2, _d, _dw, _half, 1.0, vol_tol=vt)
# the cone's seam on the far side; a chamfer (its cut does not reach the
# line on the boss, as the flush boss's did); the foot and the boss's top
_dt = _plate().fuse(_cone(15, 5, 180.0)).removeSplitter()
_dtw = _wide().fuse(_cone(15, 5, 180.0)).removeSplitter()
drafted_csg("boss_drafted_turned_foot_r1", _dt, _dtw, _half, 1.0)
drafted_csg("boss_drafted_chamfer_r1", _drafted, _drafted_wide, _half, 1.0, chamfer=True)
drafted_csg("boss_drafted_foot_and_top_r1", _drafted, _drafted_wide, _half, 1.0,
            (_foot(_drafted) + _foot(_drafted, 13.0), _foot(_drafted_wide) + _foot(_drafted_wide, 13.0)))
# two on one side; one against a round plate's rim from inside
_d2 = Part.makeBox(40, 20, 3).fuse(_cone(10, 5)).fuse(_cone(28, 5)).removeSplitter()
_d2w = Part.makeBox(40, 40, 3, App.Vector(0, -20, 0)).fuse(_cone(10, 5)).fuse(_cone(28, 5))
drafted_csg("boss_drafted_two_feet_r1", _d2, _d2w.removeSplitter(), _half, 1.0)
_dr = _rim(90.0).fuse(_cone(15, 0, 90.0)).removeSplitter()
_drw = Part.makeCylinder(40, 3).fuse(_cone(15, 0, 90.0)).removeSplitter()
drafted_csg("boss_drafted_rim_foot_r1", _dr, _drw, Part.makeCylinder(20, 100, App.Vector(0, 0, -20)),
            1.0)
_seamrim = _boss(0, 90.0, _rim(0.0))
fillet_case("boss_rim_seam_foot_r1", _seamrim, _foot(_seamrim), 1.0, "xfail")
_corner = _boss(5, x=5.0)
fillet_case("boss_corner_foot_r1", _corner, _foot(_corner), 1.0, "xfail")
_inset = _boss(8)
fillet_case("boss_inset_foot_r1", _inset, _foot(_inset), 1.0, "pass", 2592.4413, 1e-4, bop=True)
# The foot in two equal halves, the boss's seam opposite the tangent point:
# the walk past that point at the stripe's end ran on round the first half
# to the seam and stopped on it, its last point given the spine's end
# parameter, out of order, and the line could not be approximated
# (README.md, "A walk past a closed spine's end"). Refused before; now the
# volumes of the boss turned any other way. The drafted boss the same, and
# the rim's boss with its seam opposite the point.
_halves = _boss(5, 90.0)
for r, vol in ((0.3, 2585.9842), (1.0, 2591.8420), (2.0, 2611.2741)):
    fillet_case("boss_flush_halves_foot_r%g" % r, _halves, _foot(_halves), r, "pass", vol, 1e-5,
                vol_tol=1e-3, bop=True)
_dh = _plate().fuse(_cone(15, 5, 90.0)).removeSplitter()
_dhw = _wide().fuse(_cone(15, 5, 90.0)).removeSplitter()
drafted_csg("boss_drafted_halves_foot_r1", _dh, _dhw, _half, 1.0)
_rimhalves = _boss(0, 180.0, _rim(90.0))
fillet_case("boss_rim_halves_foot_r1", _rimhalves, _foot(_rimhalves), 1.0, "pass", 4561.6566, 1e-5,
            vol_tol=1e-3, bop=True)
# The boss's own seam through the tangent point (turned three quarters): the
# walks past the stripe's ends stopped on the seam, and what they made, all
# on the plate's top run on past the side, was kept for that point on an
# arc; then the seam has to be split where the fillet's line meets it
# (README.md, "The boss's seam through the point"). Refused before; now the
# volumes of the boss turned any other way. The drafted boss the same, and
# its chamfer (the cylinder's stays refused: boss_flush_chamfer_r1).
_seam = _boss(5, 270.0)
for r, vol in ((0.3, 2585.9842), (1.0, 2591.8420), (2.0, 2611.2741), (4.0, 2691.5445)):
    fillet_case("boss_flush_seam_foot_r%g" % r, _seam, _foot(_seam), r, "pass", vol, 1e-5,
                vol_tol=1e-3, bop=True)
_ds = _plate().fuse(_cone(15, 5, 270.0)).removeSplitter()
_dsw = _wide().fuse(_cone(15, 5, 270.0)).removeSplitter()
for r in (0.3, 1.0, 4.0):
    drafted_csg("boss_drafted_seam_foot_r%g" % r, _ds, _dsw, _half, r)
drafted_csg("boss_drafted_seam_chamfer_r1", _ds, _dsw, _half, 1.0, chamfer=True)


# x16win's chamfer at a corner of two fillets: a 40x30x10 block, fillet 2 on
# the edges at y=30 (the two verticals, the top one) and on (0,30,0)-(0,0,0),
# then chamfer 1 on the top edge x=0. The chamfer runs on along the mitre of
# the fillet on y=30's top edge and the one on its vertical, to their corner,
# where both turn flush with the back face. The block as a polygon extruded
# made a "valid" solid, BOP's check clean, whose corner patch had three edges
# with curves stopping 0.3819 short of their vertices, the vertices raised to
# 0.382 to cover it: 11864.0665, where a fine mesh of it gave 11909.63. From
# makeBox (the faces' edges the other way round) it was refused, as upstream
# refuses both. Now the chamfer is carried past the corner until it reaches
# the back face, its last section the cut: both alike, 11909.6170. With two
# distances one side reaches the back face first and runs on over it.
def chamfer_corner(block):
    def at(s, a, b):
        return s.Edges[edge_between(s, a, b) - 1]
    ends = [((0, 30, 0), (0, 30, 10)), ((0, 30, 0), (0, 0, 0)), ((40, 30, 0), (40, 30, 10)),
            ((40, 30, 10), (0, 30, 10))]
    return block.makeFillet(2, [at(block, a, b) for a, b in ends])


_cpoly = chamfer_corner(Part.Face(Part.makePolygon(
    [V(0, 0, 0), V(40, 0, 0), V(40, 30, 0), V(0, 30, 0), V(0, 0, 0)])).extrude(V(0, 0, 10)))
_cbox = chamfer_corner(Part.makeBox(40, 30, 10))
for tag, s in (("poly", _cpoly), ("box", _cbox)):
    for d, vol in ((1.0, 11909.6170), ((1.0, 1.5), 11901.8128), ((1.5, 1.0), 11901.8128)):
        fillet_case("chamfer_fillet_corner_%s%s" % (tag, "" if d == 1.0 else "_%g_%g" % d), s,
                    edge_between(s, (0, 0, 10), (0, 28, 10)), d, "pass", vol, 1e-4,
                    chamfer=True, bop=True)

# The chamfer sweep's mini_ab_r3 V1:1,3,6,11 (four edges at the vertex
# (38.5, 10.2, -9.75), three chamfers there): a run in four or so hung. Two
# of the three chamfers have no face in common, and ExtentThreeCorner
# extended their spines by distances it had left unset -- whatever the stack
# held, -inf or NaN at times, and the walk on a guide from NaN never ends.
# Now such a corner is refused ("two chamfers on no common face"), every
# time, in a second; not extending the pair instead made #962's like corners
# at 0.3 BOP-dirty and at 1 invalid. A hang here is the run that never
# reaches its summary.
abr3 = Part.read(os.path.join(HERE, "..", "draft", "sweep", "shapes", "mini_ab_r3.brep"))
for r in (0.3, 1):
    for k in range(4):
        sound_case("mini_ab_r3_chamfer_V1_%g_%d" % (r, k), abr3, [1, 3, 6, 11], r, chamfer=True)

# Two fillets ending at a vertex of four edges on no common face -- the
# filleted edges opposite round the vertex, a sharp edge between them on
# each side -- get the corner plate; where that result is invalid the
# opposite corner stands in: each fillet ended as alone, the two ends
# sharing the vertex as the union of the two made alone has it (README.md,
# "The opposite corner"). The reference is that union, made here of the two
# single fillets, which take the ordinary path.
def opposite_case(name, shape, edges, radius, vol_tol=None, max_tol=None, bop=True,
                  expect="pass"):
    try:
        a, b = (shape.makeFillet(radius, [shape.Edges[i - 1]]) for i in edges)
        ref = a.common(b).fuse(a.cut(shape)).fuse(b.cut(shape))
        if not ref.isValid():
            report(name, False, False, "the union of the two alone is invalid")
            return
    except Exception as e:
        report(name, False, False,
               "EXCEPTION on a fillet alone: " + str(e).strip().splitlines()[-1])
        return
    fillet_case(name, shape, list(edges), radius, expect, ref.Volume, max_tol, vol_tol=vol_tol,
                bop=bop)


def roof_block(sx=1.204, sy=1.127):
    """#631's V11 in miniature: a 13x22x40 block standing on a hip roof -- z <=
    sx x and z <= sy y, the ridge through the origin -- its corner on the
    ridge. The block's two feet, from the origin along x and along y, are
    filleted edges opposite round the vertex with no face in common; the
    block's corner edge and the ridge are the sharp edges between them."""
    def halfspace(n):
        n = V(n)
        n.normalize()
        b = Part.makeBox(400, 400, 400, V(-200, -200, -400))
        b.Placement = App.Placement(V(), App.Rotation(V(0, 0, 1), n))
        return b
    base = Part.makeBox(40, 40, 60, V(-20, -20, -40))
    roof = base.common(halfspace((-sx, 0, 1))).common(halfspace((0, -sy, 1)))
    return roof.fuse(Part.makeBox(13, 22, 40, V(0, 0, -20))).removeSplitter()


_roof = roof_block()
_feet = [edge_between(_roof, (0, 0, 0), (0, 20, 0)), edge_between(_roof, (0, 0, 0), (13, 0, 0))]
for r in (0.3, 1.0, 2.0, 3.0):
    # the foot along y given first: the plate invalid at every radius; the
    # corner exact (1e-10)
    opposite_case("roof_block_feet_r%g" % r, _roof, _feet, r, vol_tol=1e-6)
    # the foot along x first: the plate's result is valid, loose (0.028 at
    # 1) and within 0.1 of the union (0.09 at 3), so it stands -- the
    # opposite corner only takes the place of an invalid one
    opposite_case("roof_block_feet_x_first_r%g" % r, _roof, _feet[::-1], r, vol_tol=0.1,
                  max_tol=0.05)
# #631's V11, the Fillet's input: edges 16 and 23, the plate invalid at 0.3
# and 1, the corner within 2e-8 of the union
for r in (0.3, 1.0):
    opposite_case("issue631_opposite_e16_e23_r%g" % r, p631f, [16, 23], r, vol_tol=1e-4)
# #474's Fillet003, V5: edges 5 and 21, the plate invalid at 0.3 and 1. Not
# the opposite corner's: neither fillet's cap reaches the other's spine edge
# (edge 5 is a coil, 82 long, back on the vertex's line), and on both sharp
# edges the nearer contact is the vertex itself -- the ends are not two ends
# alone, the corner is refused. The plate's invalid result set back since
# (README.md, "Corners set back where the plate's result is invalid"): valid,
# clean by BOP's check, 0.07 under the union
opposite_case("issue474_f003_opposite_e5_e21_r0.3", p474, [5, 21], 0.3, vol_tol=0.1)
# #962's rail, V36 to V39: the top's edge and the slope's edge of a tooth,
# at 0.3 the plate invalid. One spine's edge meets the other's cap at the
# vertex only, the other's lies in the plane of the first's cap; each sharp
# edge has one contact from the caps, the short one's nearer contact the
# first fillet's own line ending on it. The union to 1e-4. At 1 the plate's
# result is valid (0.63 off the union) and stands
for _v, _es in ((36, (52, 74)), (37, (52, 82)), (38, (54, 84)), (39, (54, 92))):
    opposite_case("issue962_opposite_v%d_e%d_e%d_r0.3" % ((_v,) + _es),
                  Part.read(os.path.join(HERE, "..", "draft", "sweep", "shapes",
                                         "issue962_Fillet.brep")),
                  list(_es), 0.3, vol_tol=1e-4)


# A result built but invalid where a corner was the plate: those corners set
# back by the setback fallback, as where the computation fails at them
# (README.md, "Corners set back where the plate's result is invalid").
def sweep_shape(name):
    return Part.read(os.path.join(HERE, "..", "draft", "sweep", "shapes", name + ".brep"))


# #962's groove between two teeth: the floor's edge at the mouth (convex) and
# a wall's foot (concave, carried on along the wall's pieces), a corner of
# opposite concavity at four edges, the slope overhanging the mouth. The
# plate's result invalid at 0.3 and 1 (5.8 too much at 0.3; upstream's
# invalid at 0.3, refused at 1);
# set back, valid and clean by BOP's check, 2e-3 under the union of the two
# alone at 0.3 and 0.06 at 1 -- a patch where the union stands the wall's
# fillet over the floor edge's round
for _inp, _rows in (("issue962_Fillet", ((36, (52, 80), 11584.2958, 11585.8637),
                                         (37, (52, 81), 11584.2958, 11585.8637),
                                         (38, (54, 90), 11584.2958, 11585.8648),
                                         (39, (54, 91), 11584.2958, 11585.8652))),
                    ("issue962_Chamfer", ((34, (49, 72), 11697.9881, 11699.5560),
                                          (35, (49, 73), 11697.9881, 11699.5560),
                                          (36, (51, 82), 11697.9881, 11699.5572),
                                          (37, (51, 83), 11697.9882, 11699.5576)))):
    for _v, _es, _v03, _v1 in _rows:
        for _r, _vol in ((0.3, _v03), (1.0, _v1)):
            fillet_case("issue962_%s_groove_v%d_e%d_e%d_r%g"
                        % ((_inp[9:].lower(), _v) + _es + (_r,)),
                        sweep_shape(_inp), list(_es), _r, "pass", _vol, vol_tol=1e-3, bop=True)
# #474's coil standing on the block: the coil's edge with the block's upright
# edge, which carries it on in line, beside a tangent edge (V5 and V9 of the
# Fillet's input; README.md). Invalid at 0.3 and 1, set back now, clean by
# BOP's check
fillet_case("issue474_coil_v5_e5_e20_r0.3", sweep_shape("issue474_Fillet"), [5, 20], 0.3,
            "pass", 1881.6755, vol_tol=1e-3, bop=True)
fillet_case("issue474_coil_v9_e12_e25_r1", sweep_shape("issue474_Fillet"), [12, 25], 1.0,
            "pass", 1844.2334, vol_tol=1e-3, bop=True)

# #474's Fillet003, the coil leaving its block: the block's top edge (V1) or
# bottom edge (V5) beside the coil's foot, a corner of opposite concavity at
# four edges, the plate's. The block edge's line on the block's top runs on
# past the vertex to the block's far end; the plate took that end's parameter
# on the far edge as one on the sharp edge beside it, and the stripe's end
# out there, the corner across the fillet. At 1 the setback fallback finds
# nothing valid; the plates made again, stepped back on their sharp edges
# only to points on them (README.md, "A common point on another edge"):
# valid, clean by BOP's check
for _v, _es, _vol in ((1, (6, 10), 1988.4351), (5, (6, 21), 1988.6625)):
    fillet_case("issue474_f003_coilfoot_v%d_e%d_e%d_r1" % ((_v,) + _es),
                sweep_shape("issue474_Fillet003"), list(_es), 1.0, "pass", _vol,
                vol_tol=1e-3, bop=True)

# #273's Fillet001: edge 12, a B-spline wall's edge on the plane at z 18, at
# 0.3. The setback fallback's corner of more than three edges projects a curve
# on a B-spline surface (CurveHermite), and the projection's search for where
# it leaves the surface bisected for ever: its tolerance there was below the
# spacing of doubles (README.md, "A
# bisection that could not end"). Read as it is: written out and read back,
# two planes' axes change in their last digits and it never got there. Refused
# now, in seconds; a hang is this case's failure, the summary line missing
sound_case("issue273_f001_e12_r0.3_ends",
           Part.read(os.path.join(HERE, "sweep", "shapes", "issue273_Fillet001.brep")), 12, 0.3)
# #273's Fillet001, the handle's top rounded since (F14 at its end, F15 and
# F16 along it): the pocket's rim E39 at 0.3. Its end at the apex is cut off
# the top as in the handle (above), into the round beyond: the fillet and
# the round, both tangent to the top, touch where the fillet's line meets
# the top's end, and no intersection found their curve -- refused. The
# curve now through their points (README.md, "The cut off the face into a
# round"); the base corner set back. 0.162 off, the rim's strip about 0.155
# with its ends. No bop: the input fails BOP's check itself.
fillet_case("issue273_f001_apex_off_round_e39_r0.3",
            Part.read(os.path.join(HERE, "sweep", "shapes", "issue273_Fillet001.brep")), 39, 0.3,
            "pass", 8534.9956, vol_tol=1e-3)
# Its mirror E40: the stripe ends where its side on the wall meets the
# apex's edge (E45), its point on the top 0.26 short of the top's end, and
# the cut off the top was taken only from a point on the top's edge --
# refused. Its line on the top runs on to that edge: its end there is the
# point now (README.md, "The cut off the face from the line's end"). As E39,
# 0.0002 apart; both rims at once 8534.8383, within 0.005 of the two alone.
fillet_case("issue273_f001_apex_line_end_e40_r0.3",
            Part.read(os.path.join(HERE, "sweep", "shapes", "issue273_Fillet001.brep")), 40, 0.3,
            "pass", 8534.9958, vol_tol=1e-3)
fillet_case("issue273_f001_apex_both_rims_e39_e40_r0.3",
            Part.read(os.path.join(HERE, "sweep", "shapes", "issue273_Fillet001.brep")), [39, 40],
            0.3, "pass", 8534.8383, vol_tol=1e-3)
# The same with the flat end at a vertex, as FreeCAD's Fillets from version 1
# make them: each rim ends at the apex, nothing cut past it into the round,
# 0.0036 less taken than the cut above. E40's line on the top runs on past
# the stripe's point to the top's end; the flat end took the line's end for
# the point, found it on the top's edge, and was not made (the cut above
# instead) -- the point is now found on the line (README.md, "The flat end
# where the line runs on"). Both rims: the apex's edge E45 filleted too, the
# three making the corner in the tip (README.md, "Both rims: the tip
# filleted"; 8534.8383 before, as without the flat end).
for e, vol in ((39, 8534.9992), (40, 8534.9994)):
    fillet_case("issue273_f001_apex_flat_e%d_r0.3" % e,
                Part.read(os.path.join(HERE, "sweep", "shapes", "issue273_Fillet001.brep")), e,
                0.3, "pass", vol, vol_tol=1e-3, flat=True)
fillet_case("issue273_f001_apex_flat_both_rims_e39_e40_r0.3",
            Part.read(os.path.join(HERE, "sweep", "shapes", "issue273_Fillet001.brep")), [39, 40],
            0.3, "pass", 8535.2232, vol_tol=1e-3, flat=True)
# The base rim E38 the same: its line runs on past both base corners (79
# deg), and with the flat end the cut ran past each, 0.05 at 0.3, 0.15 at
# 0.8; now flat at both, nothing past them (8535.096796 and 8534.727931
# before).
for r, vol, tol in ((0.3, 8535.09671, 2e-5), (0.8, 8534.7369, 1e-3)):
    fillet_case("issue273_f001_base_flat_e38_r%g" % r,
                Part.read(os.path.join(HERE, "sweep", "shapes", "issue273_Fillet001.brep")), 38,
                r, "pass", vol, vol_tol=tol, flat=True)
# realthunder/FreeCAD#360 ("Fillet produces a spike"): the Support body's
# Fillet008, four edges of a block standing out of the front at 4 on
# Fillet007. The stored result runs to z 51.4 on a part 10 to 30 high. Its
# input, as stored, has a vertex at a tolerance of 37.2 (Pad016's, the
# reporter's 2021 build; Pad016 recomputed now is at 1e-7): that one is
# kept as it was stored (_stored, BOP's check fails on the input itself),
# and the chain recomputed now is the other (_base). Both made without
# the spike now, the same volume; on the recomputed input clean by BOP's
# check, the convex three equal to the boolean of single fillets. No code
# change: the spike is not made on the fork (README.md, "#360").
fillet_case("issue360_f008_four_edges_r4",
            Part.read(os.path.join(MODELS, "issue360_fillet007_base.brep")), [28, 29, 30, 31],
            4.0, "pass", 85451.6916, vol_tol=1e-3, bop=True, within=True)
fillet_case("issue360_f008_convex_three_r4",
            Part.read(os.path.join(MODELS, "issue360_fillet007_base.brep")), [28, 29, 30],
            4.0, "pass", 85420.6738, vol_tol=1e-3, bop=True, within=True)
fillet_case("issue360_f008_stored_input_r4",
            Part.read(os.path.join(MODELS, "issue360_fillet007_stored.brep")), [29, 31, 30, 28],
            4.0, "pass", 85451.6916, vol_tol=1e-3, within=True)
# A result BRepCheck finds invalid is refused (README.md, "An invalid result
# refused"): #962's floor edge E6 at 0.3 and 0.8, #273's E38 at 2, #876's
# chamfer of E100 at 0.8, each made invalid before.
for _inp, _e, _r, _ch in (("issue962_Fillet", 6, 0.3, False), ("issue962_Fillet", 6, 0.8, False),
                          ("issue273_Fillet", 38, 2.0, False),
                          ("issue876_Fillet", 100, 0.8, True)):
    refused_case("%s_invalid_refused_e%d_r%g%s" % (_inp[:8], _e, _r, "_chamfer" if _ch else ""),
                 sweep_shape(_inp), _e, _r, chamfer=_ch)
# #474's Fillet003, E2 and E18 at 10: invalid before (tolerance 0.097 and
# 0.055); refused now, the long extension is tried after, and it makes them.
for _e, _vol in ((2, 1988.8725), (18, 1988.8729)):
    fillet_case("issue474_f003_invalid_long_extension_e%d_r10" % _e,
                sweep_shape("issue474_Fillet003"), _e, 10.0, "pass", _vol, vol_tol=1e-3,
                bop=True)

counts = {}
for _, verdict, _ in results:
    counts[verdict] = counts.get(verdict, 0) + 1
emit("---")
emit("summary: " + "  ".join("%s=%d" % kv for kv in sorted(counts.items())))
failed = counts.get("FAIL", 0)
if counts.get("UNEXPECTED-PASS"):
    emit("NOTE: xfail case(s) now pass - promote them to 'pass' with their volume.")
sys.stdout.flush()
os._exit(1 if failed else 0)
