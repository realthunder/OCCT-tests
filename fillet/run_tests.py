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
                chamfer=False, vol_tol=None):
    """makeFillet(radius, [Edge<edge_index>]); edge_index may be a list;
    makeChamfer(radius, ...) with chamfer=True.

    expect='pass':  a valid solid, one closed shell, the input left as it was,
                    ref_volume when given (within vol_tol when given, else
                    RELTOL of it), and no edge or vertex tolerance above
                    max_tol when given.
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
            if abs(r.Volume - ref_volume) > (vol_tol if vol_tol is not None
                                             else RELTOL * abs(ref_volume)):
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


def sound_case(name, shape, edge_index, radius, expect="pass"):
    """The fillet may be refused, but a shape it makes must be a valid solid
    with one closed shell; the input must be left as it was either way."""
    before = signature(shape)
    try:
        indices = edge_index if isinstance(edge_index, list) else [edge_index]
        r = shape.makeFillet(radius, [shape.Edges[i - 1] for i in indices])
        ok = r.isValid() and len(r.Shells) == 1 and r.Shells[0].isClosed()
        detail = "vol=%.4f" % r.Volume if ok else "invalid result, vol=%.4g" % r.Volume
    except Exception as e:
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
# leaving the circle at an angle (README.md).
fillet_case("seam_end_top_r2", bc, top, 2.0, "pass", 1087.3009)
fillet_case("seam_end_bottom_r2", bc, bottom, 2.0, "pass", 1087.3009)
fillet_case("mirror_top_r2", bc, mtop, 2.0, "pass", 1087.3009)
fillet_case("mirror_bottom_r2", bc, mbottom, 2.0, "pass", 1087.3009)
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
# A chamfer on the chain from 1 on: the chain turns from the rib's top down
# its front on an arc of radius 1, and the chamfer's line on the wall turns
# back on itself there -- a self-intersecting wire, on the refined shape as
# well (1 is refused on both). Refused before, at the foot; invalid now.
fillet_case("issue962_rib_chamfer_1.2", p2, rib, 1.2, "xfail", chamfer=True)


def slant_block(mirror=False):
    """A 12x3 prism (y 0..3) whose top is flat (z=10) for x 0..4 and slopes
    down to z=6 at x=12; its front wall (y=0) split by a vertical edge at
    x=5, where the slope is at z=9.5 -- the rib above in miniature."""
    prof = Part.Face(Part.makePolygon([V(0, 0, 0), V(12, 0, 0), V(12, 0, 6), V(4, 0, 10),
                                       V(0, 0, 10), V(0, 0, 0)]))
    s = prof.extrude(V(0, 3, 0))
    s = s.generalFuse([Part.LineSegment(V(5, 0, 0), V(5, 0, 9.5)).toShape()])[0].Solids[0]
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
for tag, mirror in (("", False), ("_mirror", True)):
    rf = rib_foot(mirror)
    rfe = edge_between(rf, (0, 3, 0), (3 if mirror else -3, 3, 3))
    for r in (0.8, 1.2, 1.5, 2.0):
        fillet_case("rib_foot_split%s_r%g" % (tag, r), rf, rfe, r, "pass",
                    538.5 - (1 - math.pi / 4) * r * r * (3 * math.sqrt(2) + 2 * csb * r),
                    2e-4, vol_tol=1e-4)


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
# dereference that took the process down; it failed after that fix, its
# far corner (-17,16.75,3) leaving the stripe's end without a point. The
# corner setback fallback makes it: both corners set back where the fillets
# meet (fcad docs/CornerBlending.md section 9). The edges run between nearly
# coplanar drafted walls, so the fillets move the volume by thousandths.
p876 = Part.read(os.path.join(MODELS, "issue876_fillet_base.brep"))
c876 = [edge_between(p876, (17, 16.75, 0), (17, 16.75, 3)),
        edge_between(p876, (-17, 16.75, 3), (17, 16.75, 3)),
        edge_between(p876, (19.238761, 15.746985, 3), (17, 16.75, 3)),
        edge_between(p876, (17, 16.75, 3), (17, 16.442791, 20.6))]
for r, vol in ((0.3, 8665.7840), (1.0, 8665.7870)):
    fillet_case("issue876_corner4_r%g" % r, p876, c876, r, "pass", vol)


def refused_case(name, shape, edge_index, radius):
    """The fillet is refused, and the input left as it was."""
    before = signature(shape)
    indices = edge_index if isinstance(edge_index, list) else [edge_index]
    try:
        r = shape.makeFillet(radius, [shape.Edges[i - 1] for i in indices])
        ok, detail = False, "made: valid=%s vol=%.4f" % (r.isValid(), r.Volume)
    except Exception as e:
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
# tighter: tolerance 0.013 before, 1e-4 now); at radius 1 it cannot be, and
# the fillet is computed again with the end a break point, as before.
p474b = Part.read(os.path.join(MODELS, "issue474_fillet001_base.brep"))
e474b = edge_between(p474b, (-9, 0, 11), (-9, 0, 16))
for r, taken in ((0.3, 3.56632), (1.0, 40.25303)):
    fillet_case("issue474_f001_e12_r%g" % r, p474b, e474b, r, "pass", p474b.Volume - taken)

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
