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
RELTOL = 1e-4


def emit(line):
    # FreeCAD redirects sys.stdout into its own console, which swallows
    # script output under FreeCADCmd - write straight to fd 1.
    os.write(1, (line + "\n").encode())


# FreeCAD freezes shape values when it finds this fork, and a frozen input is
# protected from an algorithm that edits it. Run unfrozen by default, as any
# other build of FreeCAD runs, so such an edit shows (FILLET_FREEZE=1 for the
# frozen path).
App.ParamGet("User parameter:BaseApp/Preferences/Mod/Part").SetBool(
    "ImmutableShapeValues", os.environ.get("FILLET_FREEZE", "0") != "0")


def signature(shape):
    """What a fillet must leave of its input: the shape valid, the volume."""
    return (shape.isValid(), round(shape.Volume, 6))


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
                chamfer=False):
    """makeFillet(radius, [Edge<edge_index>]); edge_index may be a list;
    makeChamfer(radius, ...) with chamfer=True.

    expect='pass':  a valid solid, one closed shell, the input left as it was,
                    ref_volume when given, and no edge or vertex tolerance
                    above max_tol when given.
    expect='xfail': known broken (see README.md); an exception, an invalid
                    shape or an open shell counts as the expected failure.
    """
    try:
        before = signature(shape)
        indices = edge_index if isinstance(edge_index, list) else [edge_index]
        op = shape.makeChamfer if chamfer else shape.makeFillet
        r = op(radius, [shape.Edges[i - 1] for i in indices])
        problems = []
        if signature(shape) != before:
            problems.append("input changed: valid=%s vol=%.4f" % signature(shape))
        if not r.isValid():
            problems.append("invalid")
        if len(r.Shells) != 1:
            problems.append("shells=%d" % len(r.Shells))
        elif not r.Shells[0].isClosed():
            problems.append("open-shell")
        if not problems and ref_volume is not None:
            if abs(r.Volume - ref_volume) > RELTOL * abs(ref_volume):
                problems.append("volume %.4f != %.4f" % (r.Volume, ref_volume))
        if not problems and max_tol is not None:
            tol = max([e.Tolerance for e in r.Edges] + [v.Tolerance for v in r.Vertexes])
            if tol > max_tol:
                problems.append("tolerance %.3g > %.3g" % (tol, max_tol))
        ok = not problems
        detail = "; ".join(problems) if problems else "vol=%.4f" % r.Volume
    except Exception as e:
        ok = False
        detail = "EXCEPTION " + str(e).strip().splitlines()[-1]
    report(name, ok, expect == "xfail", detail)


def nocrash_case(name, shape, edge_index, radius):
    """The fillet may fail, but must not take the process down; the input
    must be left as it was either way. A crash ends the run: the missing
    summary line is the failure."""
    before = signature(shape)
    try:
        r = shape.makeFillet(radius, [shape.Edges[edge_index - 1]])
        detail = "valid=%s vol=%.4f" % (r.isValid(), r.Volume)
    except Exception as e:
        detail = "refused: " + str(e).strip().splitlines()[-1]
    ok = signature(shape) == before
    report(name, ok, False, detail if ok else "input changed; " + detail)


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
# The bottoms are built as the tops are, but the corner's curve on the
# cylinder meets the face's circle at fourth order, within 2e-9 of it over
# its last 1%, and BRepCheck's 2D intersection sees it cross (README.md);
# on the tops it happens not to.
fillet_case("seam_end_top_r2", bc, top, 2.0, "pass", 1087.3009)
fillet_case("seam_end_bottom_r2", bc, bottom, 2.0, "xfail")
fillet_case("mirror_top_r2", bc, mtop, 2.0, "pass", 1087.3009)
fillet_case("mirror_bottom_r2", bc, mbottom, 2.0, "xfail")

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
e50 = edge_between(p2, (38.5, 10.2, -3.75), (38.5, 10.2, 14))
fillet_case("issue962_e50_r0.3", p2, e50, 0.3, "pass", 11583.8075)
fillet_case("issue962_e50_r0.8", p2, e50, 0.8, "pass", 11581.7204, 0.05)
# Edge 56, e50's mirror image across the block (y=27.2 for 10.2): its foot is
# the five-face corner at (38.5,27.2,-3.75), filled by a plate held tangent to
# the stripe, which missed its boundary by 0.09 and folded; the approximation
# strayed 0.48, the corner kept tolerances up to 1.18 and a face whose volume
# integrates to anything from 2.0 to 5.0 taken. Built again on positions
# alone it takes what e50 takes.
e56 = edge_between(p2, (38.5, 27.2, -3.75), (38.5, 27.2, 14))
fillet_case("issue962_e56_r0.8", p2, e56, 0.8, "pass", 11581.7068, 0.05)
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


# #474's Fillet003 input, edge 6: its corner plate missed its boundary by 1.8
# at radius 2 -- invalid, tolerances 15 to 36, 244 too much volume at r 2.
p474 = Part.read(os.path.join(MODELS, "issue474_fillet003_base.brep"))
for r, vol in ((0.3, 1988.9101), (0.8, 1989.1235), (2.0, 1990.2561)):
    fillet_case("issue474_f003_e6_r%g" % r, p474, 6, r, "pass", vol, 0.05)

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
# surface, and the projection threw where Perform tries another surface. The
# volumes taken are too small for the whole shape's (about 0.002 of 11584):
# validity is the check.
e36 = edge_between(p2, (38.5, 27.2, -3.75), (38.5, 27.2, -9.75))
for r in (0.1, 0.3):
    fillet_case("issue962_e36_r%g" % r, p2, e36, r, "pass")


def arm_on_tall_block(split=True):
    pts = [V(17.356, -9.425, -9.75), V(38.5, 10.2, -9.75), V(38.5, 27.2, -9.75),
           V(10.898, 16.471, -9.75)]
    arm = Part.Face(Part.makePolygon(list(reversed(pts)) + [pts[-1]])).extrude(V(0, 0, 6))
    bp = [V(38.5, 27.2, -9.75), V(38.5, 10.2, -9.75), V(50, 10.2, -9.75), V(50, 27.2, -9.75)]
    s = Part.Face(Part.makePolygon(bp + [bp[0]])).extrude(V(0, 0, 23.75)).fuse(arm)
    if split:
        cut = Part.LineSegment(V(38.5, 27.2, -3.75), V(50, 27.2, -3.75)).toShape()
        s = s.generalFuse([cut])[0].Solids[0]
    return s


atb = arm_on_tall_block()
top = edge_between(atb, (38.5, 27.2, -3.75), (38.5, 27.2, -9.75))
for r in (0.1, 0.3, 2.0):
    fillet_case("arm_on_tall_block_r%g" % r, atb, top, r, "pass")
# The block's side one face: the line on it runs on up past the arm's top,
# and the arm's top, extended to meet it, crossed its own edge under the
# block's wall -- invalid at every radius. Cut at the section through the
# arm's side, the corner is that of the split side.
atb = arm_on_tall_block(split=False)
top = edge_between(atb, (38.5, 27.2, -3.75), (38.5, 27.2, -9.75))
for r in (0.1, 0.3, 0.5, 2.0):
    fillet_case("arm_on_tall_block_whole_r%g" % r, atb, top, r, "pass")
# The mirror corner, the block's edge x=38.5 y=10.2 coming down onto the arm's
# top: there the arm's top, extended, is the floor of the fillet's end and
# crosses nothing, and must stay the exact plane it is (a plate in its place
# misses by 1e-2): a quarter-round's section over the edge's 17.75.
low = edge_between(atb, (38.5, 10.2, -3.75), (38.5, 10.2, 14))
for r in (0.3, 1.0, 2.0):
    fillet_case("arm_on_tall_block_down_r%g" % r, atb, low, r, "pass",
                atb.Volume - (1 - math.pi / 4) * r * r * 17.75, max_tol=1e-3)

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
# and a chamfer of that size, which walks the same way: a triangle of d^2/2
# over the spine's 9
for d in (0.7, 0.70001, 0.7001):
    s = slotted(wall=True)
    fillet_case("slot_split_wall_chamfer_d%g" % d, s, edge_between(s, (10, 3, 5), (10, 3, 14)), d,
                "pass", s.Volume - 4.5 * d * d, chamfer=True)

# realthunder/FreeCAD#876's first Fillet input: the four edges at the corner
# (17,16.75,3). The two-stripe corner there has its common points on two
# different edges and filled along a pivot it does not have -- a null
# dereference that took the process down. It fails now, as it should; this
# case is here so that the suite gets to its summary.
p876 = Part.read(os.path.join(MODELS, "issue876_fillet_base.brep"))
c876 = [edge_between(p876, (17, 16.75, 0), (17, 16.75, 3)),
        edge_between(p876, (-17, 16.75, 3), (17, 16.75, 3)),
        edge_between(p876, (19.238761, 15.746985, 3), (17, 16.75, 3)),
        edge_between(p876, (17, 16.75, 3), (17, 16.442791, 20.6))]
for r in (0.3, 1.0):
    fillet_case("issue876_corner4_r%g" % r, p876, c876, r, "xfail")

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
# quarters, its seam at (0,-3)): invalid at every radius, and too much
# taken (12 at radius 0.6), before the fix and after alike -- open.
pps = post_on_plate(turn=270)
fillet_case("post_seam_on_plate_r0.6", pps, edge_between(pps, (-12, -3, 3), (0, -3, 3)), 0.6,
            "xfail")

# The same with a drafted post (1 deg): the post's wall is a cone, the round
# end below it a cylinder, and the fillet's end must be cut by the round
# end's surface, not the cone's. Refused (a faulty vertex) -- open, as is
# #876's Fillet002 below, where the corner is the same.
ppd = post_on_plate(1.0)
fillet_case("post_draft_on_plate_r0.6", ppd,
            edge_between(ppd, (-12, -3, 3), (0, -3, 3)), 0.6, "xfail")

# realthunder/FreeCAD#876's Fillet002: its input (Fillet001's result) has a
# plate whose top outline -- two lines and an arc, one tangent chain --
# runs at both ends into a drafted corner of the tall body, the plate's side
# tangent to the round end below it. Invalid at every radius (the
# drafted-post corner above, reached through PerformIntersectionAtEnd).
p876b = Part.read(os.path.join(MODELS, "issue876_fillet002_base.brep"))
e876b = [edge_between(p876b, (-19.238761, -15.746985, 3), (-30.167832, -3.494723, 3)),
         edge_between(p876b, (30.167832, -3.494723, 3), (19.238761, -15.746985, 3))]
for r in (0.3, 0.6):
    fillet_case("issue876_fillet002_r%g" % r, p876b, e876b, r, "xfail")

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
