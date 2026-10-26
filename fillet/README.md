# Fillet regression tests

Regression suite for the fork's fixes to fillets (`TKFillet`: `ChFi3d`,
`BRepFilletAPI_MakeFillet`), the cases taken from the fillet issues of
`../occ-issues/`. Same shape as `../thickness/`: every fix gets cases here,
and the fixes are shown before and after in `models/Fillet.md`.

## Running

Any FreeCAD build linked against this OCCT tree:

```
FreeCADCmd tests/fork/fillet/run_tests.py
```

The suite runs with FreeCAD's shape values unfrozen (`ImmutableShapeValues`
off), as any build that does not freeze them runs; `FILLET_FREEZE=1` runs it
frozen. Every case also checks that its input comes back as it went in
(valid, the same volume), and every result it makes for loose ends -- an
edge whose curve ends past its vertex, which BRepCheck lets pass
(`../loose_ends.py`, added 2026-10-15) by more than the tolerance the case
accepts. Of the cases that passed, only #876's fillet a few thousandths
wide (`issue876_corner4_r0.3`, `issue876_post_foot_e10_r0.3`) is loose past
1e-4: both its lines end in one vertex, 0.0026 from each, within the 6e-3
the cases accept.

Exit code 0 = no regression (every expected-pass case passed). Known-broken
cases are marked `XFAIL` in the script; when one starts passing the suite
prints `UNEXPECTED-PASS` -- promote it to `pass` with its reference volume and
update this file. A crash ends the run before its summary line: that is a
failure too.

## A seam left on a piece of a closed face (realthunder/FreeCAD#523, 2026-10-02)

The model: a 10 box with a three-quarter cylinder of radius 2 at the corner
on the z axis, joined by Part's Connect (`models/issue523_fillet_explodes.FCStd`;
`models/issue523_box_cylinder.brep` is its Connect, the fillet's input). The
cylinder's seam is the line x=2, y=0 where it meets the box's side, and the
boolean kept it as an edge with **both** pcurves on the cylinder (u=0 and
u=2 pi) although the three-quarter face holds it once. A radius-1 fillet on
the box edge along y=0 that ends at that line came out invalid
("Unorientable shape"): the face's wire did not close in 2D, the end cap's
pcurve a period (u 0..0.52) away from the face (u 1.57..6.81).

Cause: `ChFi3d_Builder::PerformOneCorner` read the pcurve of the common
point's arc on the face at the fillet's end with `BRep_Tool::CurveOnSurface`,
which, for an edge closed on the face, picks a pcurve by the orientation of
the edge it is handed -- here the orientation the fillet data carries, not
the edge's in the face. `IntersectMoreCorner` repeats the code. Fix
`16df68d224`: `PCurveInFace` takes the edge as it occurs in the face when
the edge is closed on the face but not really closed
(`BRepTools::IsReallyClosed`), for every pcurve those corners read of an
edge not taken from the face itself. Upstream master has the same code.

| Case | What it covers |
|------|----------------|
| `issue523_document` | the captured model recomputes, its Fillet valid at 1092.5263 |
| `seam_end_top_r*`, `seam_end_bottom_r*` | the fillet on the box edge ending on the seam, top and bottom, radius 0.5, 1 and 2 |
| `mirror_*` | the same fillet on the edge across the box's diagonal, which does not end on a seam: the seam cases must give its volumes |
| `every_edge_r1_e*` | every edge of the shape at radius 1: nothing else moved |

Checked against the fix: every one of the shape's 15 edges at radius 0.5, 1
and 2 gives the same result as before except the two edges ending on the
seam; the other fillet models of `../occ-issues/` recompute as before, but
for #876's first fillets, whose vertex blend now starts on the right period
(volume -0.0173; it meets its neighbour cylinders within 1.51 deg, 1.91
before); FreeCAD's `TestPartApp` (139) and `TestPartDesignApp` (77) pass
before and after.

## A fillet line collapsed to a point (found on #523's shape, 2026-10-02)

A fillet of radius 2 on the cylinder's top or bottom arc -- the radius of the
cylinder -- has no line on the top face, only a point, and the stripe's curve
there is null. `PerformOneCorner` (through `IntersUpdateOnSame`) and
`IntersectMoreCorner` dereferenced it: SIGSEGV, the process gone. Fix
`214d858dc3`: no intersection is reported, and the fillet fails
(`StdFail_NotDone`). Upstream master has the same code.

| Case | What it covers |
|------|----------------|
| `arc_top_r2_no_crash`, `arc_bottom_r2_no_crash` | the fillet is refused, the process lives, the input is as it was |

## A corner whose faces are split in coplanar pieces (realthunder/FreeCAD#962, 2026-10-02)

The model is a PartDesign body without Refine: its walls are kept as several
coplanar faces, split by the booleans that made them. Its Fillet (radius 0.8,
twelve edges) was invalid, and five of the edges alone were too
(`models/issue962_pocket002.brep` is the Fillet's input, the body's
Pocket002). Four are the outer edges of slots cut down to a floor -- the
edge ends on the floor, which the fillet extends (`PerformOneCorner`'s
OnSame case) -- where the slot's wall is two faces, its piece at the outer
face only 0.692 or 0.787 wide. The fifth, edge 50, ends under a chamfer, and
the wall beside it (y=10.2) is two faces split at that end.

`PerformOneCorner` builds such a corner from the face Fad holding the
fillet's common point on the end face Fv, the face Fop on the other side, and
the edge Arcprol between Fv and Fop, which it extends to the fillet. Three
assumptions about those broke on split faces. Fix `cf96757c36`:

- **The fillet wider than Fad's piece at the vertex**: its common point lies
  on the next piece of the wall, so the arc it is on is not an edge of the
  vertex, and the first other edge of Fv at the vertex -- the narrow piece's
  own bottom edge -- was taken as Arcprol. Volumes off by +11 to -24 (the
  slots), invalid from radius 0.7 on. Arcprol is now the edge between Fv and
  Fop (or a face tangent to Fop); and the edges of Fv from the vertex to the
  common point's arc, which nothing else cut away (the narrow piece survived
  whole, its bottom edge dangling in the floor), go the way of the spine's
  edge.
- **Arcprol not in Fop but in Fop's tangent neighbour** (edge 50): its
  orientation in Fop defaulted to FORWARD, and Fop lost the fillet's line --
  an open wire. It is now taken from the neighbour, in the shell, and carried
  into Fop's frame.
- **The extension along the split itself**: a fin padded flush with the
  block's side (`fin_on_block_*`) -- the most ordinary of the three. The
  fillet's line on the fin's face ends on the edge between the fin's and the
  block's face, `IntersUpdateOnSame` reset the point off that edge, and the
  extension, which runs along it, was given to the fin's face: a
  self-intersecting wire at every radius. The point stays on the edge, and
  the extension bounds the block's face.

Upstream's files at the fork's base give the same results as the fork before
the fix.

| Case | What it covers |
|------|----------------|
| `slot_split_{wall,outer,both}_r*` | a block with a slot down to a floor, its wall split 0.7 from the outer face, its outer face split below the floor, or both: each must give the unsplit slot's volume, radius 0.5 to 2 |
| `issue962_e10{1,2,4,5}_r0.8` | the model's slots: all four at 11580.7739 (identical slots) |
| `issue962_e50_r0.3`, `issue962_e50_r0.8` | the edge under the chamfer |
| `fin_on_block_r*`, `fin_arc_on_block_r*` | a fin flush with the block's side, flat or with a top arc tangent to its outer face; the flat one must remove what the slot does |
| `fin_on_block_wall_r0.3` | the same fin, its wall split as the slot's, narrower than the piece |

Checked against the fix: every edge of 22 shapes -- the inputs of the fillet
and chamfer features of #273, #474, #631, #876 and #962, #309's and #523's
shapes, and small models of each case -- at radii 0.3, 0.8 and 2: 112
results go from invalid to valid (#962's Pocket002 and Pad004 among them),
the other 3590 are the same as before. FreeCAD's `TestPartApp` (139) and
`TestPartDesignApp` (77) pass.

## A seam cut at both ends by two corners (realthunder/FreeCAD#962, 2026-10-02)

With the five edges above fixed, #962's Fillet was still invalid with all
twelve: edges 36 and 49, the foot of the block where the arm meets it
(x=38.5, z -9.75..-3.75), were each valid alone, and the Fillet without
either one was valid, but the two together came out invalid, 7225 too large.
The bottom is two coplanar faces, the arm's and the block's, split along
x=38.5 from y=27.2 to y=10.2. `PerformIntersectionAtEnd` builds both corners
across that seam: e36's convex fillet cuts it at y=27.186, e49's concave one
meets its line at y=10.136 -- past the seam's end. Each corner gave the seam
a point interference at its parameter, the second one outside the edge's
range; alone, the face rebuild turns that into a lengthened edge, but with
the other corner's cut on the same edge it built both -- the cut edge
(27.186..10.2) and the lengthened one (10.136..27.2) -- in both faces. It
turns on the seam's direction: with the seam running the other way the
point falls before the edge's start, and that composes.

Fix `b38f0d910c`: across a seam of tangent faces, a point past the seam's end at
the corner's vertex is not given to the seam; the piece of the seam's line
from the vertex to the point becomes a curve of its own on both faces (the
way the corner extends a face's edge when it has to extend the face), and
the seam is left whole for the other corner. Only tangent seams: on a sharp
edge (e49's top, where the arm's top meets the block's side) the curve did
not close the faces, and the lengthening works there.

| Case | What it covers |
|------|----------------|
| `issue962_e36_e49_r0.8` | the pair: the sum of the two alone |
| `issue962_fillet_r0.8` | the Fillet, all twelve edges |
| `arm_on_block_foot_r*` | an arm fused to a block, the seam between their bottoms from y=27.2 to 10.2: the pair at radius 0.5, 0.8 and 1.5 gives what the two give alone |

Checked against the fix: the every-edge sweep (22 shapes, plus this slab)
is unchanged, 3762 results -- one edge at a time never met this; FreeCAD's `TestPartApp` (139) and `TestPartDesignApp` (77)
pass. The fork before the fix fails the five new cases.

An aside found on the way: edge 56 alone reports a volume 5.04 smaller than
its input where its mirror image, edge 50, reports 2.35 -- the faces match
change for change, and a mesh of the result gives 2.2. The corner's blend is
a B-spline far larger than its trimmed piece, and the volume integration
over it is off; the shape is right.

## A fillet ending on a wall kept in coplanar pieces (2026-10-02)

The last of the corner cases above, left open by the fix there: the fin
padded flush with the block's side, its wall split 0.7 from the outer face
as the slot's (`fin_on_block_wall_*`). Each of the two alone works -- the
slot with the split wall, the fin with the whole one -- and so did the two
together up to radius 0.5; from 0.7 on, `StdFail_NotDone`, a walking
failure.

With the wall split, the fillet's support at the spine is the wall's
narrow piece, and its line on the wall lies on the wide piece, whose edge
on the floor stops at x=9.3, short of the spine's end vertex (10,3,5). The
walk along the spine stops at z=5, where the fin's face ends; on the slot
the outer face goes on below the floor, and one walk takes the fillet past
it into the extension. `StartSol`, restarting the walk there, takes an
edge of the end that does not touch the spine's end vertex for an
obstacle: the floor became a face to roll along, and the walk failed.
Behind it, `PerformOneCorner` counted only the fin's common point as on
the vertex, took the block's side for the end face instead of the floor,
and threw "bouchon non ecrit" (the cap is not written).

Fix `2ac4fee0c6`: `ChFi3d_EdgeOnSplitToVertex` follows such an edge along
the end face, through faces tangent to its own across edges of the way, to
the vertex. `StartSol` takes it for the end, as the whole wall's edge, and
the corner counts the common point as on the vertex, classifying the
vertex with the edge the arc continues as there. From there on the corner
is the slot's: the narrow piece's edge on the floor goes with the spine's
edge.

| Case | What it covers |
|------|----------------|
| `fin_on_block_wall_r{0.3,0.8,2}` | the fin flush with the block, its wall split as the slot's: what the unsplit fin takes |

Checked against the fix: every edge of 25 shapes (the sweep's 22, the
slab, the split fin and the split slot) at radii 0.3, 0.8 and 2: 2 results
go from failing to valid -- the split fin's own edge at 0.8 and 2 -- and
the other 3919 are the same. FreeCAD's `TestPartApp` (139) and
`TestPartDesignApp` (77) pass.

A radius within about 1e-4 of the piece's width, 0.7, stayed open; see
below.

## A corner plate whose boundary curve missed its first surface (realthunder/FreeCAD#962, 2026-10-02)

Edge 36 of #962 alone -- the arm's side against the block's side at its
foot, 21 degrees apart -- failed below radius 0.42 with a faulty vertex at
its top (38.5,27.2,-3.75). Above the arm the block goes on, its side
y=27.2 two coplanar faces split at the arm's top, and five faces meet at
the vertex. `PerformIntersectionAtEnd` hands such a corner to
`PerformMoreThreeCorner`, which fills it with a `GeomPlate` patch. With the
fillet that narrow (its lines 0.19 r off the edge), one of the patch's
boundary curves had no projection at all on the plate's first surface, and
`GeomPlate_BuildPlateSurface::ProjectCurve` read the bounds of the first
projected piece without asking whether there was one:
`Standard_NoSuchObject`. A curve without a continuous projection is what
`Perform` falls back on other first surfaces for -- the plate's
approximation, then the plane -- and the plane takes all four curves.

Fix `2b9df66c48` (TKGeomAlgo): no projected piece is a null curve, as no
continuous one is. The patch fits within 1.4e-3, the fillet is valid at
every radius, and the volume it takes grows with r^2 as the sliver's does
-- measured on the result cut down to a box around the edge, since the
whole shape's volume (11584) is too large for GProp to see 0.002 in.

| Case | What it covers |
|------|----------------|
| `issue962_e36_r{0.1,0.3}` | the edge in #962's Pocket002: valid (no volume: the change is below GProp's precision on the whole shape) |
| `arm_on_tall_block_r{0.1,0.3,2}` | the same corner made small: the arm fused to a block that goes on above it, the block's side split at the arm's top |

Checked against the fix: the every-edge sweep, 25 shapes: 2 results go from
an exception to valid (the edge, and the same corner in #962's Chamfer's
input), 3914 are the same, and 5 go from an exception to an invalid shape
-- #474 Fillet003's edge 52 at every radius, and #876's front edge at
radius 2 in both of its fillets. Those corners now get past the plate and
fail further on (in #474 a second plate fits only to 0.058); the sweep
holds 140 other invalid results, which is how this API fails as often as
it throws. PartDesign's Fillet reports either as an error; `Part::Fillet`
and `makeFillet` hand the invalid shape back. FreeCAD's `TestPartApp`
(139), `TestPartDesignApp` (77) and `TestSurfaceApp` pass.

Followed up (2026-10-03): #876's two went back to exceptions with the
projection fix `68c5d4efd0`. #474's edge 52 is the input's: the sweep's
Fillet003 shape holds a sliver face at the edge's end vertex, a plane 2
tall and 4.5e-7 wide (area 9e-7), which leaves a pair of near-coincident
vertical edges at each end of the edge. The result is the input's volume
at every radius -- nothing cut -- and invalid. Not pursued: the input is
what is wrong there.

Found on the way, open (XFAIL): the same corner with the block's side one
face, `arm_on_tall_block_whole_r0.5`, is invalid at every radius, with the
fork before the fix as after -- the arm's top is extended past the block's
wall by the fillet's reach (0.1875 r) and its wire crosses itself. (Fixed
since: "A fillet's end under a wall that runs on past the corner", below.)

## A corner plate folded to stay tangent (realthunder/FreeCAD#962, 2026-10-02)

Edge 56 of #962 alone took 5.04 of volume where its mirror image, edge 50,
took 2.35 -- and a mesh of the same result said 3.5, GProp's adaptive mode
2.0. The shape was not right. Its foot is the five-face corner at
(38.5,27.2,-3.75), which `PerformMoreThreeCorner` fills with a `GeomPlate`
patch held G1 -- tangent -- to the stripe it closes. The plate missed its
own boundary by 0.092 on a fillet of 0.8, and folded over 1/30 of its area
to meet its constraints; the approximation, allowed ten times the plate's
miss, strayed 0.48, so the corner's edges were stored with tolerances of
0.48 to 1.18 (BRepCheck passes them for it), and a pcurve of the patch
looped over itself. Edge 50's plate missed by 0.011 and strayed 0.19: no
fold, but tolerances of 0.195 on a fillet of 0.8.

It is no rare plate. Over the every-edge sweep, of the 495 corner plates
built, 413 missed their boundaries by more than 1e-3 and 87 by more than
0.1, a few by thousands; the code's own comment says G1 constraints "very
often cause unpredictable undulations". A G0 plate -- positions alone --
fitted edge 56's boundary within 3.6e-4.

Fix (`PerformMoreThreeCorner`): a plate that misses its boundary by more
than `ChFi3d_Builder::PlateG0Fallback()` is built again from the same
boundaries at G0, and taken if it fits better; its edges are then not
marked tangent to the stripes. A crease along the stripe instead of a
fold. The distance is a global setting, `ChFi3d_Builder::SetPlateG0Fallback()`
(and `ChFi3d_SetPlateG0Fallback`, extern "C", for a caller that looks it up
at run time -- FreeCAD's Part preference `FilletPlateG0Fallback` does, so a
FreeCAD built against upstream OCCT still loads). Default 1e-3;
`Precision::Infinite()` keeps every tangent plate, as upstream does.
(Since 2026-10-05 a fraction of the radius decides; see "The plate
fallback relative to the radius" below.) Only
static functions were added: the toolkit's ABI is unchanged. Edge 56 takes 2.433 by every
measure now (GProp's default and adaptive modes agree to 1e-4), edge 50
2.420, tolerances 0.014 and 0.009.

| Case | What it covers |
|------|----------------|
| `issue962_e56_r0.8` | edge 56: e50's volume, tolerances under 0.05 |
| `issue962_e50_r0.8` | edge 50 now also held to tolerances under 0.05 (it had 0.195) |
| `issue474_f003_e6_r{0.3,0.8,2}` | #474's Fillet003 input, edge 6: invalid at every radius (tolerances to 36, 244 too much volume at r 2), valid now |

Checked against the fix, at the default 1e-3: the every-edge sweep, 25
shapes, with each result's largest edge or vertex tolerance: 20 results go
from invalid to valid, 156 valid ones end with less than half their
tolerance (#474's edge 17 at 0.8: 41.6 to 0.002; #273's edge 16 at 2: 9.6e5
to 0.18), none gets a larger one, and 2 go from valid to invalid: #962's
edge 33 at 0.3, in the Fillet's input and the Chamfer's. That corner's G1 plate was no better --
its outline crossed itself ten times and its surface folded, and the
"valid" fillet of radius 0.3 removed 9.4 of volume where 0.6 is due --
and the G0 one, which fits ten times better, has two of its boundary
curves meeting head to head, which BRepCheck now rejects. (Both were one
fault, not the plates': see the next section. Edge 33 is valid at either
plate now, and takes 0.55.) At 1e-2 the
change is smaller -- 17 valid, 107 tighter, the same 2 lost -- and leaves
the merely mediocre G1 plates (edge 36's at 0.8, 3.3e-3) as they were; at
1e-3 those are rebuilt too (edge 36's tolerance 0.0215 to 0.0123), most of
the corners in all. FreeCAD's `TestPartApp` (139),
`TestPartDesignApp` (77) and `TestSurfaceApp` pass.

## A plate boundary stored backwards (realthunder/FreeCAD#962, 2026-10-03)

Edge 33 of #962 -- the arm's top on its side, ending at the five-face corner
(38.5,10.2,-3.75) under edge 50 -- came out invalid at 0.3 once the corner's
plate was G0, and its "valid" G1 result before that took 9.4 of volume
where 0.55 is due. A mesh of that same G1 result took 0.555: the shape was
right and GProp was reading it wrong, on one face -- the block's side
y=10.2, whose area it put at 62.1 for 69.

`PerformMoreThreeCorner` closes the corner with curves laid on the faces
between the stripes' ends, each stored as running from the end of stripe
`ic` to that of `icplus`: the first DS point at its first parameter, the
second at its last. Where the curve is a projection taken from
`CurveHermite`, it keeps the direction `BRepAlgo_NormalProjection` built it
in, and here that was the other way. Its edge, the 0.3 on y=10.2, got its
FORWARD vertex at its last parameter -- the vertices are each on the curve
at their own parameters, so BRepCheck passes it, but anything walking the
edge by its range walks it backwards: GProp's area lost 2 x 11.5 x 0.3. And
the same curve was the plate's second boundary, head to head with the
first; `PlateOrientation` read each curve from its first parameter, so its
corner there was the far end, and with the G0 plate its two sums disagreed
in sign and the plate face was turned over (negative area, BRepCheck's
bad orientation).

Fix `3fa9420429`: a projection that runs from `icplus`'s end to `ic`'s is
reversed, 2D and 3D together (when the two still share one parameter range
after it; else it is left as it was). And `PlateOrientation` takes the
plate's `Sense()`, walking a boundary that runs against the others from its
last parameter. With the first change no plate in the sweep below has such
a boundary any more (none of 495); the second is what `GeomPlate` reports
the order by, and alone it was enough to make edge 33 valid, though not to
make its volume right.

| Case | What it covers |
|------|----------------|
| `issue962_e33_r{0.1,0.3}` | edge 33: valid, taking 0.062 and 0.554 (they were invalid, 3.0 and 9.4) |

Checked against the fix: the every-edge sweep, 25 shapes, 3921 results:
the 2 lost to the G0 plate are valid again, and 10 results that were valid
already change -- #962's edges 29 to 32 (31 and 32 in the Fillet's input,
29 and 30 in the Chamfer's), edges ending at edge 33's corner or at its
mirror image (38.5,27.2,-3.75). Each had
an edge or vertex tolerance equal to the radius and now has 0.007 to 0.12,
and each volume moves to what a mesh of the result says: edge 32, concave,
17 long, now adds 0.330 at 0.3 and 14.94 at 2 ((1 - pi/4) r^2 L: 0.328 and
14.6), where GProp had it taking 9.8 and 49. Nothing else moves, status or
tolerance. FreeCAD's `TestPartApp` (139), `TestPartDesignApp` (77) and
`TestSurfaceApp` pass.

## A corner's curve over several faces (2026-10-03)

The fix above covers the curves `PerformMoreThreeCorner` lays on one face.
When the faces under two stripes' ends differ (`moresurf`), the curve
between them is projected on each face in turn and stored in pieces, with
the same two assumptions: that each projection runs from `ic`'s end to
`icplus`'s, and that the faces come in the order the curve crosses them.
A piece that did not start at `ic`'s end started where the piece before it
ended -- `ind`, which is 0, no point of the DS, for the first one.

No single-edge fillet reaches that code. A vertex sweep does -- at every
vertex of the 25 sweep shapes, all its edges, every pair and each alone,
at 0.3 and 1, about 11000 fillets -- 40 times, all on split walls and
corners an edge too short for the radius overflows (#962, #876, the split
wall shapes below). No piece ran backwards, but the order did not hold: at
#962's chamfer, corner (38.5,13.7,14), the first face's piece is the one
that ends at `icplus`, and it and two others took point 0. Each of those
fillets fails at another corner first, so nothing showed it.

Fix `f1d8509ff6`: a piece whose ends match the chain the other way round is
reversed, as above, and a point between pieces is made once, by whichever
piece reaches it first, and given to the other. The 40 come out as they
did; it is a guard, with no case yet to show it.

## A two-stripe corner with no pivot (realthunder/FreeCAD#876, 2026-10-03)

The same vertex sweep stopped dead on both of #876's Fillet inputs: the
four edges at the corner (17,16.75,3), at 0.3 or 1, took FreeCAD down.
`ChFi3d_FilBuilder::PerformTwoCorner`, when the stripes' common points on
the faces are distinct, fills between them along the pivot -- the edge both
lie on -- and only looks the pivot up when both are on the same edge. Here
each is on an edge of its own, and the fill trimmed a null curve.

Fix `76a730386a`: such a corner goes to `PerformMoreThreeCorner`, as the
other corners this code cannot build already do. It still fails, with an
exception the caller gets. Both sweeps of #876 now run to the end, 2088
fillets; what the old build reached is unchanged, and so are the other 23
shapes and the every-edge sweep.

On the way, the other corner of those edges, (-17,16.75,3), threw out of
`ProjLib_CompProjectedCurve`'s `FindSplitPoint`, which takes the nearest of
a point's projections without asking whether there is one (index -1).
Stopping that, the projection went on into `BRepAlgo_NormalProjection`,
which read the curve of an approximation that had built none (its error
reads 0). Fix `ce5aa60088` drops such an approximation.

| Case | What it covers |
|------|----------------|
| `issue876_corner4_r{0.3,1}` | XFAIL then, an exception: the process survives to the suite's summary (the build before `76a730386a` dies here, exit 139); made since, see "The corner setback fallback" |

## A projection's split point with no point on the surface (realthunder/FreeCAD#876, 2026-10-03)

`FindSplitPoint` splits a curve where it crosses a periodic surface's
border: it projects each candidate point on the surface and keeps it if the
projection is on the border. The search finds only extrema inside the
surface; a point whose nearest is on the boundary has none, and it took
"the nearest" of none, index -1. Here the point was the start of a range the
recursion opened just past a split already found, 7e-5 from the cylinder's
seam at (-17,16.75,3). Fix `2ab42e74f6`: such a point is not a split.

Alone that made things worse: 99 fillets of #876 (E10 at every radius, E30
to E32 at 0.8 and 1, their mirror images, and edge sets with them) went from
an exception to an invalid shape, none to a valid one. Past the split, the
corner's `CurveHermite` projected its curve on the faces between the
stripes, and the pieces did not run end to end. At (-17,16.75,3) E10's
stripe ends 0.007 wide and the curve runs along the edge x=-17 between the
two faces: on both at once, each projection kept half, the first face the
curve's end and the second its start. For E30 at 1 the first face's piece
runs from (-17,16.75) to (-19.24,15.75) and the curve starts at (-14,13.9).
The curves stored from such pieces joined the wrong points; the volume came
out anything (+11, -278).

Fix `68c5d4efd0`: the first piece present must touch the curve's start (at
either of its ends; a backward one is turned round where it is stored, see
above) and the last its end, or the corner fails. Swapping such pieces was
tried and made none of the 99 valid -- the piece on the B-spline face lies
on the edge of the surface's parameter domain and does not project there
either.

With both: no valid result moves in the every-edge sweep or the vertex
sweep; 11 and 56 invalid results become exceptions, and nothing goes the
other way. (The vertex sweep runs every fillet of a shape on one copy of
it, and a fillet that fails can leave that input changed for the next: two
of #876's results came out differently by order alone. Run on a fresh copy
each, #876's two shapes change only in 48 invalid results becoming
exceptions.)

## A fillet as wide as the piece of a split wall (2026-10-03)

The last of the split-wall cases: the slot and the fin above, their wall
split 0.7 from the outer face, at a radius within the walk's tolerance
(1e-4) of 0.7. The fillet's line on the wall then runs along the split
itself, its whole length. 0.69999 and 0.701 worked; 0.7 and 0.70001 failed
to start (`StartsolFailure`), and 0.7001 came out invalid.

Two things stood in the way. The walk starts and goes on only at points IN
both faces (`BRepBlend_Walking::PerformFirstSection`, and each step after
it), and a line along the split is ON the boundary of both pieces,
everywhere. And where it did start (0.7001), on the wide piece, the line's
ends fell on the split's vertices, and the corners had nothing to cut away
the narrow piece with: the wide piece kept the split and the fillet's line
side by side, a slit of no width, and the narrow piece stayed whole beside
the fillet -- an unorientable shell.

Fix `98c6125b85`, in three parts:

- **The walk's domain.** On the far piece, a point that is ON only the
  split toward the piece the spine is on, and on the face's own side of
  it, is IN: the piece the spine is on goes under the fillet whole, the far
  piece keeps all of itself. The split must be tangent and must not touch
  the spine -- a side of the spine's face that meets the spine at its end
  (#474's Fillet003, edge 18, a B-spline ring face) is crossed by the line,
  not followed, and treating it so turned a walking failure into an invalid
  shape.
- **The split under the line.** When the line on a face runs from vertex to
  vertex along such a split, each corner cuts the split away from its end,
  as it cuts the spine's edge.
- **The end face at a convex corner.** The edges of the end face from the
  vertex to a common point beyond the face beside it lie under the fillet
  -- the narrow piece's top edge here. Only the corner `OnSame` (concave
  spine, the floor) cut them away; the corner of three convex edges (the
  top) does now as well.

Every radius from 0.69995 to 0.7001 gives the unsplit slot's volume, the
fillet a quarter cylinder of the radius over the spine's 9.

| Case | What it covers |
|------|----------------|
| `slot_split_{wall,both}_r{0.7,0.70001,0.7001}` | the slot, its wall split (and its outer face too): the unsplit slot's volume |
| `fin_on_block_wall_r{0.7,0.70001,0.7001}` | the same on the fin flush with the block |
| `slot_split_wall_chamfer_d{0.7,0.70001,0.7001}` | a chamfer of that size on the slot, which walks the same way (it failed or came out invalid as the fillet did): 1130 - 9 d^2/2 |

The every-edge sweep (3921 fillets of 25 shapes) has nothing else move: no
valid result changes its volume or tolerance, and no status changes.
FreeCAD's `TestPartApp` (139) and `TestPartDesignApp` (77) pass.

## A fillet's end under a wall that runs on past the corner (2026-10-03)

The open case of the plate fix above: the arm fused to the taller block,
the fillet on the arm's edge against the block's side y=27.2, that side one
face from the floor to the block's top. Split at the arm's top, the corner
is valid; whole, it was invalid at every radius.

The fillet is a cylinder, and each of its lines is clipped to its own face:
the one on the arm's side stops at the arm's top (z=-3.75), the one on the
block's side runs on to the block's top (z=14). The end vertex has four
edges, one line ends on an edge of it and the other does not, and
`PerformIntersectionAtEnd` hands such a corner to `IntersectMoreCorner`. That
extends the face at end -- the arm's top -- to cut the line on the block's
side, and takes the face beyond the arm top's other edge at the vertex to
be the block's side again or tangent to it. Here it is the block's face
x=38.5, standing on the arm's top: the arc of the section on the extended
arm top runs under it, across the arm top's own edge, and the arm top's
wire crossed itself. What lies there is not the arm's top at all but a
ceiling under the block, facing down.

Fix `692cae9e35`: the corner first checks whether the arm top's other
edge at the vertex runs into the corner between the vertex and the
section's two points (`SectionCrossesEndFace`). If it does, the line on the
block's side is cut at the section through the arm side's end -- where an
edge splitting the block's side there would cut it -- and the corner is
filled as the split side's is, with the corner plate. The result is the
split block's to within 0.5% of the volume the fillet takes, and its
plate's tolerance is no worse (0.0216 at radius 3, 0.0249 split).

The test is the crossing, not the face beyond being tangent: the mirror
corner, the block's edge x=38.5 y=10.2 coming down onto the arm's top, has
a face beyond that is not tangent either (the arm's other side), but there
the extended arm top is the floor of the fillet's end, faces the arm top's
way, and crosses nothing. `IntersectMoreCorner` makes it exactly; a plate
in its place misses by 1e-2 (a first version of the fix did that, and the
sweep showed 13 valid results turn to exceptions and 6 invalid, #962 and
#474's edges coming down onto a step among them).

| Case | What it covers |
|------|----------------|
| `arm_on_tall_block_whole_r{0.1,0.3,0.5,2}` | the corner with the block's side one face: valid (no volume: the change is below GProp's precision on the whole shape). Held to its exact volume since 2026-10-13, the plate gone: "A ceiling under a wall at a fillet's end" |
| `arm_on_tall_block_down_r{0.3,1,2}` | the mirror corner: the exact floor, the volume of a quarter-round's section over the edge's 17.75, tolerance under 1e-3 |

The every-edge sweep (3921 fillets of 25 shapes) is the same to the last
digit. The vertex sweep -- at every vertex of the same shapes and the two
arm blocks, all its edges together, each pair and each alone, at radii 0.3
and 1: 12722 fillets -- moves 12 results, all on the unsplit arm block, all
from invalid to valid: the edge at radius 0.3 and 1, alone and with the
other edges of its two vertices. FreeCAD's `TestPartApp` (139) and
`TestPartDesignApp` (77) pass.

## An end point a rounding error past the line (realthunder/FreeCAD#523, 2026-10-03)

#523's box and cylinder at radius 2, the cylinder's own radius. The
fillet's line on the top runs to the cylinder's top circle and is tangent
to it there, at the line's very end: (0, 2, 10) for the edge ending on the
seam, (2, 0, 10) for its mirror image across the box's diagonal. The
corner (`PerformOneCorner`, `OnSame`) cuts the line with the cylinder
extended past its face; the intersection finds the tangent point at W = -2,
and the line's range starts at -2.0000000000000071 on the seam's side but
-1.9999999999999938 on the other. 6e-15 past the end, the point was thrown
away, nothing else was found, and the corner was refused ("bouchon non
ecrit", `StdFail_NotDone`) -- on one side and not the other.

Fix `efbe5c99fd`: `Update` (curve against surface), when no point lies on
the curve's range, takes one within `Precision::PConfusion()` of an end as
that end -- where the curve is tangent to the surface there, the case in
which the point is ill-conditioned along the curve. Only as a fallback:
taking such a point over one on the range broke the cylinder's own arcs at
radius 1 (`every_edge_r1_e11`, `e13`). And only at a tangent point: a
crossing found past the end is past the end -- taking those (#962's
0.05-long edge 1, with fillets of 0.3 and more) turned its exception into
an invalid shape.

`mirror_top_r2` passes now, at the seam case's volume. The bottoms --
`seam_end_bottom_r2`, and `mirror_bottom_r2`, which got as far now --
are built as the tops are and come out "Self-intersecting wire" on the
cylinder. They are not wrong by any measure but that one. The corner's
curve on the extended cylinder ends at the far vertex tangent to the
circle the bottom cuts there, and leaves it at fourth order (z = x^4/64):
over its last 1% it stays within 2e-9 of the circle. All four corner
curves, tops and bottoms, are the same curve to 1e-11, running up to
1.6e-9 past the face there against an edge tolerance of 1e-7. BRepCheck's
2D intersection, at 1e-10, sees the bottoms cross the circle 0.025 from the
vertex, and excuses a crossing only within the vertex's tolerance (1.3e-7)
or where both edges keep within twice their tolerance of the straight line
to it (the circle's sag alone is 4e-5 there). On the tops it does not find
the crossing. Radius 1.999 and below is valid on all four; above 2 all
four are refused (the fillet's end then meets the box's side as well as
the cylinder; see "Past the cylinder's radius", below). The bottoms are
valid since: "A corner's curve kept on its face", below.

| Case | What it covers |
|------|----------------|
| `mirror_top_r2` | the edge across the diagonal at radius 2: valid, the seam case's volume |
| `mirror_bottom_r2` | XFAIL then, as `seam_end_bottom_r2`; valid since, see "A corner's curve kept on its face" |

The every-edge sweep moves those two results and nothing else (3919 the
same to the last digit); the vertex sweep (12722 fillets, radii 0.3 and 1)
moves nothing. FreeCAD's `TestPartApp` (139) and `TestPartDesignApp` (77)
pass.

## Past the cylinder's radius (realthunder/FreeCAD#523, 2026-10-05)

The box and cylinder of #523, the four box edges ending at the cylinder (the
seam edges at the top and bottom, and their mirror images), at a radius
above the cylinder's 2: every one is refused. The corner is `OnSame`:
Arcpiv the seam, Fv the cylinder, Fop the top. `PerformOneCorner` cuts
the fillet's line on the top, y = r, with the cylinder carried on,
x^2 + y^2 = 4 -- and above 2 they do not meet. `IntersUpdateOnSame`
returns false and the corner throws "bouchon non ecrit"
(`Standard_NotImplemented`). Handing it to `PerformIntersectionAtEnd`
does not help: that hands it back, or fails to find an edge.

What the end should be, by a boolean -- the fillet's groove carried past
the end, less the cylinder, cut from the shape -- which gives the fillet's
own volume at radius 1 and 2: the cut runs over two faces meeting at a
sharp edge, the cylinder carried into the box for y < 2 up to the edge
x = 0, y = 2, and the box's side x = 0 from there to the top at y = r.
The cylinder's face closes around at the top (the arc carried on over the
whole quarter, so the face wraps the whole circle there), and the top
splits in two: the disk and the rest of the square beyond y = r. Radius
2.5 gives 1083.3063, 3 gives 1078.3294. None of that is in
`PerformOneCorner`: its cut over two faces (`FvT`) needs them tangent
across a straight edge and leaves every face in one piece. Open, tracked
here.

The cylinder's own arcs above radius 2 are refused, and rightly: a convex
fillet on a circle of radius 2 cannot be wider than 2.

| Case | What it covers |
|------|----------------|
| `seam_end_top_r{2.5,3}`, `mirror_top_r{2.5,3}` | XFAIL then, refused; made since with the end set back, see "The corner setback fallback" (the boolean's volumes are those of the end run past) |

## A fillet's end on the edge where its side runs into a wall (realthunder/FreeCAD#876, 2026-10-04)

#876's Pocket "added material" because Fillet002 came out invalid (an open
shell once FreeCAD's FixShape had dropped its bad faces; FreeCAD now
refuses both, fcad `bb6c4ea481`). Its edges are a plate's top outline,
which at each end runs into a corner of the tall body beside it: the
plate's side is tangent to the body's rounded corner there, which is a
cylinder below the plate's top and a 1 deg cone (the body's draft) above.

Made small without the draft (`post_on_plate`): a post, a cylinder of
radius 3, on a stadium-shaped plate whose side y=-3 runs tangent into the
plate's round end under the post. The plate's top pinches out between the
side and the post's base at (0,-3,3), where the fillet's edge ends. The
corner (`PerformOneCorner`, `OnSame`) cuts the fillet with the post's
cylinder extended down past its face. On the side face the cut ends at
(0,-3,3-r) -- on the edge between the side and the round end, the side
being tangent to the cylinder along it -- and the extension from there to
the vertex is that edge's upper piece. It went into the side face, which
kept the whole edge too: its wire ran up to the top and back down, and the
result was invalid at every radius.

The corner already handles a fillet line ending on such an edge (`Etan`,
between Fop and the face tangent to it, `zobOnEtan`): the edge is split at
the line's end and the extension bounds the tangent face, not Fop. Fix
`538ce9f99a` takes that path also when the line ended inside Fop and the cut
moved its end onto `Etan` -- provided Fv's surface holds `Etan` from there
to the vertex, so that the extension runs along it. The extension's curve
on the tangent face is then moved onto that face's period at the vertex:
projected on the cylinder it landed one period off (u = 3pi/2 against the
face's -pi/2), and the face's wire did not close in its domain. The
volume is what the fillet removes outside the post's cylinder, computed
from the corner prism by booleans.

With the draft the post's wall is a cone, which does not hold the edge
below it, and the vertex has four sharp edges, so it went to
`PerformIntersectionAtEnd` instead: refused on the small model, invalid on
#876's own (see "A drafted wall at the fillet's end", below). The post
turned so that its own seam runs through the edge's end was invalid at
every radius, taking far too much, in upstream and the fork alike (see
"The extension on the cut's side of a seam", below).

| Case | What it covers |
|------|----------------|
| `post_on_plate_r{0.1,0.6,2}` | the post on the plate: valid, the volume outside the post's cylinder (invalid at every radius before) |

The every-edge sweep (4431 fillets, #876's Fillet002 input and the post
models added) turns 12 invalid results valid -- the post's two edges along
the side, and two edges of #962's own inputs, the Chamfer's 7 and the
Fillet's 4, at every radius, their volumes as they were -- and moves
nothing else (2412 valid results the same to the last digit, tolerances
too). The vertex sweep (14274 fillets) turns 46 invalid results valid
(28 of the post, 12 of #962's Chamfer, 6 of its Fillet), changes one
invalid result's volume in the fourth decimal, and nothing else. FreeCAD's
`TestPartApp` (139) and `TestPartDesignApp` (78) pass.

## A drafted wall at the fillet's end (realthunder/FreeCAD#876, 2026-10-04)

The post on the plate with its post drafted 1 deg (`post_on_plate(1.0)`),
and #876's own Fillet002, whose tall body's corners are drafted the same
way. The post's wall is a cone now and the round end below it still a
cylinder, so the edge between them is sharp, and the vertex at the
fillet's end has four sharp edges: the spine, the post's base on the top,
that cone/cylinder edge, and the side/round end edge, which the count
takes as sharp because the plane and the cylinder are tangent but not
G2. `PerformExtremity` gives the spine's end a status from the three
edges of a three-edge corner only; at four it stays a break point, the
walk runs on along the post's base edge (a second SurfData on the edge),
and the corner goes to `PerformIntersectionAtEnd` and on to the plate,
whose curve pieces do not run end to end: refused.

But the side and the round end are one wall in two faces, tangent across
their edge: with that edge left out the vertex is the undrafted post's
corner of three, the fillet ending OnSame against the post. Fix
`5310ff9d59` (`PerformExtremity`) does that when the vertex has four edges
and four faces, and exactly one of the three edges beside the spine joins
a face of the spine to a face it runs on into, tangent within the
builder's angular tolerance; the end is OnSame when the other three say
so, and `PerformFilletOnVertex` sends an OnSame end at four sharp edges to
`PerformOneCorner`, which already finds the edge to extend through the
tangent face. Both limits came from the sweep: with the 0.1 rad that
`IsTangentFaces` takes by default, a 1.5 deg kink beside a spine on #474's
helical ramp counted as one wall, and with no count of faces, a vertex of
five on #309; their corners went to `PerformOneCorner` and failed, where
the walk past a break point had made them (38 results valid before). And
whether the corner of three can be made depends on the radius: on #474's
Fillet001 it is at 0.3 and 0.8 and not at 1. Where such a corner fails,
`Compute` runs again with that end a break point, as before, and puts the
state back for the next computation (30 results of the vertex sweep valid
again). The fillet is cut by the post's cone
carried on below its base, as the undrafted post's is by its cylinder;
the side face keeps a thin piece between the cut and the side/round end
edge, closing to a cusp at the vertex where the side is tangent to the
cone's base circle. The volume is the corner prism outside that cone, by
booleans. FreeCAD's `Volume` is 1.4e-3 short of it at radius 0.6 on the
result; adaptive GProp (`VolumeProperties` with an epsilon) agrees with
the booleans to 3e-7 -- the default integration misses on the cusp.

On #876's model the corners at y=+15.7 then pass; at y=-15.7 the post's
wall is a `Geom_RectangularTrimmedSurface` around a cone, trimmed at the
plate's top, and `PerformOneCorner` extends only B-spline and Bezier
surfaces: the cut's point lies below the trim and the line/cone
intersection found nothing ("bouchon non ecrit"). The same fix takes a
trimmed surface's basis there. #876's whole document recomputes: Fillet002
(0.6) valid, and the Pocket after it takes material away.

At radius 1 the line on #876's top passes the end of the cone's base arc
(41 deg of it; radius 1 needs 48) onto the base edge of the drafted wall's
plane, which the cone continues tangent to: the face at the end comes in
two pieces and the one reached does not hold the vertex -- open then, made
since ("The cut over a drafted wall's cone and plane", below).

| Case | What it covers |
|------|----------------|
| `post_draft_on_plate_r{0.1,0.6,2}` | the post drafted 1 deg: valid, the corner prism outside the cone (refused before) |
| `post_draft{3,10}_on_plate_r0.6` | drafted 3 and 10 deg (refused, and invalid with 12 taken, before) |
| `issue876_fillet002_r{0.3,0.6}` | #876's Fillet002 on its input (`models/issue876_fillet002_base.brep`, Fillet001's result): valid (invalid, an open shell, before) |
| `issue876_fillet002_r1` | XFAIL then, the face at the end in two tangent pieces; made since, see "The cut over a drafted wall's cone and plane" |
| `issue474_f001_e12_r{0.3,1}` | #474's Fillet001 (`models/issue474_fillet001_base.brep`), the edge up the ramp's side: the corner of three made at 0.3, and at 1, where it cannot be, the fillet computed again past a break point |

The every-edge sweep (4431 fillets) turns 24 results valid -- #876's
three models, six edges each at radius 0.3 (the plate's top chain and its
mirror), and the drafted post's two edges along the side at every radius,
refused before -- loses none, and tightens 32 valid results on #474's two
models where the ramp's drafted walls end a fillet (tolerance 0.013-0.035
down to 1e-4, volumes moving by under 0.007). On two models a tolerance
of 1e-7 reads 1.4e-6 to 6.7e-6 for every later edge: the sweep fillets one
input shape in turn, and a fillet that now succeeds there raises the
tolerance of the input's own sub-shapes it shares -- the input is not left
as it was, which the suite does not see (it checks validity and volume).
The vertex sweep (14274 fillets) turns 96 invalid results valid and 24
refused ones valid (#876's models and the drafted post), moves 210 valid
results of #474's models by at most 0.0125 (tighter, as above), loses
none, and turns 7 refused results on #876's Fillet and Fillet001 at radius
1 into invalid ones: pairs of edges whose corners are made now, after
which the result is garbage (volume -1e12) -- the same pairs at radius 0.6
come out so before the fix as well; open. FreeCAD's `TestPartApp` (139)
and `TestPartDesignApp` (78) pass.

## The extension on the cut's side of a seam (2026-10-04)

The undrafted post turned three quarters, so that its own seam runs up
from the fillet's end (`post_on_plate(turn=270)`). The corner is the one
of "A fillet's end on the edge where its side runs into a wall": the cut
on the post's cylinder runs from the post's base, at u=5.64, round to the
seam, ending at u=2pi on the cylinder's period there, as `ChFi3d_Recale`
puts it beside the base's end. The extension from that end down to the
vertex was computed from Arcprol's parameter at the vertex instead -- the
vertex is on the seam, and Arcprol gives it u=0. The post's wire then
jumped a period between the cut and the extension, did not close in the
face's domain, and the face was built inside out: invalid, 12 taken at
radius 0.6, 223 with the post drafted as well, in upstream and the fork
alike. Fix `c34722ef01`: the extension starts where the cut ends, and the
vertex's parameter is taken on that side. Where the vertex is on no seam
the two are within half a period and nothing moves.

| Case | What it covers |
|------|----------------|
| `post_seam_on_plate_r{0.1,0.6,2}` | the post's seam through the edge's end: valid, the same volume as the post turned any other way (invalid before) |
| `post_draft_seam_on_plate_r{0.1,0.6,2}` | the same post drafted 1 deg: needs both fixes (refused, or invalid with 223 taken, before) |

Neither sweep has the seam at a fillet's end (the post there is turned a
quarter), and neither moves.

## The cut over a drafted wall's cone and plane (realthunder/FreeCAD#876, 2026-10-04)

#876's Fillet002 at radius 0.8 and up: the tall body's corner is a 1 deg
cone over 41 deg of arc on the plate's top, then the drafted wall's plane,
the cone running on into it tangent across a straight edge (a ruling).
The fillet's line on the top ends where the top does, on the cone's base
arc while r < 3(1-cos 41deg) = 0.736 -- and past that on the plane's base
edge. The corner (`PerformOneCorner`, `OnSame`) takes the face across that
edge as the face at the end and the edge to extend as one of that face at
the vertex; the plane holds no edge of the vertex, so none was found, the
corner went to `PerformIntersectionAtEnd`, and on to the plate, refused.

The wall there is the cone and the plane, one wall in two faces, and the
cut runs over both. Fix `2a623612a8`: when the face across the line's edge does
not hold the vertex, but the edge of the top from that edge's end to the
vertex has a face on its other side (the cone) which the first runs on
into, tangent, across a straight edge from that end, the cone is the face
at the end -- the edge to extend and the cut's end on the side are its, as
for a fillet whose line stays on the arc -- and the cut is made in two
pieces: on the plane from the line's end to the point where the cut
crosses the ruling carried on below the top, and on the cone from there.
That piece of the ruling goes in as an edge of both faces, and the cone's
base arc, under the fillet now, goes away. The ruling's pcurves are
projected on the faces' surfaces extended (on #876 one cone is a
B-spline, which ends at the top).

Made small (`teardrop_post`): the post on the plate drafted 1 deg, its
base the round end's circle over 41 deg of the top, then the straight wall
tangent to it, the far side closed by a second tangent wall. The removed
volume is the corner prism outside the post carried on below its base, by
booleans; the fillet matches it to under 1e-5 at every radius from 0.3 to
2, mirrored, drafted 3 and 10 deg, with 20 and 60 deg of arc, and with the
post's faces converted to B-splines (by adaptive GProp; FreeCAD's default
integration is off by more than the suite's tolerance on those). #876's
Fillet002 is valid from 0.8 to 2 (refused before), at 1.2 with the next
fix.

At #876's corner at y=-13.75 the cone is analytic with its seam on the
straight edge, and the cone's piece can be computed two ways: from the
crossing point, or from the cut's end on the side through it to the
fillet's line on the cone carried on, and cut there. Each comes out loose
at some radii -- the first next to the switch radius, the second where it
crosses the seam -- so the fix takes the one that fits better: within the
input's 1.7e-4 at most radii, 5e-4 to 1.1e-3 at a few.

| Case | What it covers |
|------|----------------|
| `post_draft_plane_on_plate_r{0.6,0.8,1,2}` | the teardrop post: 0.6 on the arc as before, 0.8 to 2 over the plane and the cone (refused before) |
| `post_draft_plane_mirror_r1`, `post_draft10_plane_on_plate_r1`, `post_draft_plane_arc20_r0.6` | mirrored; drafted 10 deg; 20 deg of arc, the line on the plane from 0.18 |
| `post_draft_plane_nurbs_r1` | the post's faces B-splines: valid (volume by adaptive GProp, README) |
| `issue876_fillet002_r{0.8,1,1.2,1.5,2}` | #876's Fillet002: valid (refused before) |

The every-edge sweep (4719 fillets, the four teardrop models added) with
this and the three fixes below turns 53 refused results valid -- #876's
three models, twelve each (the plate's top chains at 0.8 and 2), and the
teardrops -- loses none, and moves no volume of the 2596 valid before. On
the models with newly valid results the tolerances of later fillets rise:
the sweep fillets one input in turn, and a fillet that now succeeds raises
the tolerances of sub-shapes it shares with the input (a fresh input gives
the same tolerance as before). The vertex sweep (15122 fillets) turns 162
refused results valid, the same models, turns 11 invalid ones into
refusals (see "Two stripes" below), moves no volume of the 9753 valid
before, and loses none. FreeCAD's `TestPartApp` and `TestPartDesignApp`
pass.

## Two stripes at an end across a tangent split (realthunder/FreeCAD#876, 2026-10-04)

`5310ff9d59` makes an end OnSame at a vertex of four sharp edges where a
face of the spine runs on tangent into another: a corner of three, for a
fillet ending there alone. #876's plate top edge along its side and the
post's base arc beside it, filleted together, end at one such vertex: a
convex and a concave fillet, two stripes, whose corner is
`PerformMoreThreeCorner`'s plate. With the first end OnSame the plate came
out inside out (volume -2e10) at radius 1, where before it was refused.
Fix `86c8d5ad28`: the corner of two stripes at four sharp edges with an
end OnSame is refused, and `Compute` runs again with that end a break
point, as it does for a corner of three that fails: refused again at
radius 1. With both ends break points the same plate is still inside out
at radius 0.6, and on two more pairs at radius 1, as it was before
`5310ff9d59` -- open.

| Case | What it covers |
|------|----------------|
| `issue876_side_and_post_x{+19,-19}_r1` | the two edges at either corner: refused or valid, never an invalid shape (inside out before) |
| `issue876_side_and_post_x{+19,-19}_r0.6` | refused or valid since the fix below (the plate of two break points inside out before) |

## The cut's end beside the cone (realthunder/FreeCAD#876, 2026-10-04)

The teardrop post with its faces B-splines (`toNurbs`), filleted along the
plate's other side, y=3, where the cone's arc on the top is only 12 deg:
from radius 0.9 the line on the top crosses onto the far wall well away
from the vertex, and the walk ends there. The cut's end on the side, where
the cone's surface carried on meets the fillet's line on the side, came
out at the root nearest that end -- on the B-spline cone's extension,
which curves back to meet the side 8 away -- and the cut ran over the
extension: inside out, the volume up by 50, where before `2a623612a8` the
corner was refused. An analytic cone meets the line only beside its arc.
Fix `8c91316949`: the cut's end must lie on the cone beside its base arc,
its parameters projecting inside that edge's pcurve; else the corner is
refused, as before.

| Case | What it covers |
|------|----------------|
| `post_draft_plane_nurbs_far_side_r1` | refused or valid, never an invalid shape (inside out before) |

## A vertex at the end of a corner's curve (realthunder/FreeCAD#876, 2026-10-04)

#876's Fillet002 at radius 1.2: at one corner the extension -- the curve
from the vertex down the plate's side, where the extended cone meets it --
starts 3.56e-5 off the vertex. `Compute` gives a vertex at the end of a DS
curve that curve's tolerance, which was 3.5620502505e-5; the curve's end
lay 3.5620502565e-5 away, 6e-14 farther, and BRepCheck found the vertex
off the edge: invalid. Fix `d45fc2c2b6`: the vertex takes the larger of the
two, with a margin of 1e-9 of it against rounding.

| Case | What it covers |
|------|----------------|
| `issue876_fillet002_r1.2` | valid (invalid before, the vertex off the extension by 6e-14) |

## A plate's boundary on the wrong face (realthunder/FreeCAD#876, 2026-10-05)

The open end of "Two stripes at an end across a tangent split": #876's
plate top edge along its side and the post's base arc beside it, filleted
together at radius 0.6, both ends break points -- and the same pair at the
plate's other corners, and on Fillet002's input -- came out inside out,
volume -2e11 to -2e13. The corner is `PerformMoreThreeCorner`'s plate, and
one of its four boundaries, the curve from the post's fillet's end to the
vertex on the post, was 70434 long. The two fillets are tangent at the
vertex (`deuxconges`), which skips the search for a curve over several
faces; the post's fillet, cut back for the plate past the end of the
post's round end, ends 0.42 along the post's plane beside it. Its end was
read in its pcurve on that plane -- (13.33, -8.21) -- and taken as a point
of the round end's B-spline, whose parameters run over [0, 1.57] x [0, 1];
the batten from there to the vertex ran off the surface.

Letting the search for curves over several faces run at such a corner
does not help: it is not written for it, and stops on a DS point never
made. Fix `467e37b45d`: the curve between two ends is refused when a
fillet's end lies on another face than the curve's; the corner, and the
fillet, are refused. The vertex sweep (15122 fillets) moves 11 results,
all from invalid to refused -- these pairs at radius 1, and the teardrop
posts' (`mini_tear*`) pairs of the same kind; nothing valid moves, and the
edge sweep is the same to the last digit.

| Case | What it covers |
|------|----------------|
| `issue876_side_and_post_x{+19,-19}_r0.6` | refused (inside out before) |
| `issue876_side_and_post_x-19_y-16_r1` | the pair at the corner (-19, -16): refused (inside out before) |
| `issue876_fillet002_side_and_post_r{0.6,1}` | the pair at Fillet002's corner (19, -16): refused (inside out before) |

## The cone piece's tolerance (realthunder/FreeCAD#876, 2026-10-05)

The cut over a drafted wall's cone and plane (above) left #876's Fillet002
with tolerances of 5e-4 to 1.8e-3 at the corner y = -13.75, the input's
own being 1.7e-4. Two causes. The ruling's line between the pieces, exact
on both faces, was stored with the larger of the pieces' tolerances, as
were both pieces. And the cone piece itself came out loose:
`ChFi3d_ComputeCurves` walks the intersection and approximates the walk,
and the walk's points, a deflection of 1e-3 of the chord apart, left the
curve up to 1.1e-3 off the surfaces between them (1e-5 at the mirror
corner, walked with more points). It is not the cone's seam: the piece
computed on the cone turned half a turn comes out the same to every digit.

Fix `222d8da037`: each piece keeps its own tolerance, the point between
them the largest; and a walk whose curve misses `tol3d` is walked again
finer -- step halved, deflection a quarter -- up to three times, the
closest kept (a walk within `tol3d` is as before). Fillet002's largest
tolerance at 0.3 to 2 is now the input's.

| Case | What it covers |
|------|----------------|
| `issue876_fillet002_r{0.3,...,2}` | now also no tolerance above 2e-4 (5e-4 to 1.8e-3 before) |

## An extension's end off its own curve (realthunder/FreeCAD#631, 2026-10-05)

The Fillet002 input of #631: a chain of six edges round a slanted arm, ending
at (44, 36.33, 92) on the end face x = 44 -- invalid at 0.8 and 2,
"self-intersecting wire" on the end face. The corner extends the arm's
round end, a circle, past the vertex to the point where the fillet's line
on the round meets the end face; the cut on the end face ends there too,
tangent to the circle (the fillet is tangent to the round along its line).
That point is computed on the fillet's line and lies 3.7e-7 off the
circle, whose new edge kept the circle's 1e-7. BRepCheck found the cut
and the circle crossing 1.3e-3 from the vertex -- inevitable for two
curves tangent there -- and excuses such a crossing only while both edges
keep within twice their tolerance of the chord from the vertex: the
circle's edge was 3e-7 off it, the vertex's offset alone.

Fix `020c54bbbc`: after the result is built, an edge the fillet made
whose curve ends off its vertex by more than the edge's tolerance, but
within the vertex's, takes that distance. Edges of the input are left
alone; the input shares them.

| Case | What it covers |
|------|----------------|
| `issue631_fillet002_r{0.8,2}` | the chain (`models/issue631_fillet002_base.brep`): valid, the volume unchanged (invalid before) |

The two fixes together, against the build before: the every-edge sweep
turns 30 invalid results valid -- all #631's, every edge of the chains on
its three inputs at 0.8 and 2 -- makes 299 tolerances tighter and none
looser, and moves no volume; the vertex sweep turns 111 invalid results
valid (#631's, all it had), loses none, and moves #876's volumes by under
1e-4 (the cone pieces) and one #523 pair onto its mirror's value.

## The plate fallback relative to the radius (FreeCAD case 5829, 2026-10-05)

The plate fallback above took a fixed distance, 1e-3. FreeCAD's case 5829
-- a box with a wedge on its back, filleted all round at 8 -- has corner
plates that, held tangent, miss their boundary by 0.45-0.49% of the
radius: tangent to well within what a fillet of 8 shows, yet over 1e-3, so
they were rebuilt creased, and no thickness of the creased solid comes out
(PartDesign's TestThickness 5829 tests). The same miss is a fold at one
radius and nothing at a radius a hundred times larger; the
`arm_on_tall_block` corner misses by 0.47% at radius 0.1, 0.3 and 0.5
alike, and the fixed distance kept 0.1 tangent and creased 0.3. Measured
on fcad-37 over the suite's corners: 5829 0.45-0.49%, arm_on_tall_block
0.47%, #962's fillet at 0.8 0.78-0.92%, #474 Fillet003 e6 1.05-1.24%, #962
e50 1.33%, then #962 e33 6.8%, #876 Fillet002 7.4-12.5%, #962 e56 11.6%.

The rule now (the user's ruling: creased corner as a fallback relative to
the radius, gated by a setting): a plate missing its boundary by more than
`ChFi3d_Builder::PlateG0FallbackRatio()` -- default 0.01 -- times the
smallest radius (or chamfer distance) of the stripes at the corner is
built again at G0. `SetPlateG0FallbackRatio()` sets it, and
`ChFi3d_SetPlateG0FallbackRatio`, extern "C", for FreeCAD's Part
preference `FilletPlateG0FallbackRatio` (0 = off), which replaces
`FilletPlateG0Fallback`. With the ratio at 0 the distance of
`SetPlateG0Fallback()` decides, and its default is now
`Precision::Infinite()`: the fallback is off, as upstream. Static
functions only; the ABI is unchanged. At 2% two of the suite's cases
(`issue962_e50_r0.8`, `issue474_f003_e6_r2`) keep plates whose
approximations exceed their tolerance bound; at 1% none.

| Case | What it covers |
|------|----------------|
| `case5829_r8` | the fillet of `models/case5829_box.brep` (the Box feature's solid, its Fillet's twelve edges): valid, the tangent plates' volume |
| `case5829_r8_thickness` | that fillet, its large face removed, thickened 1 inward: valid (with the fixed 1e-3 the plates crease and the thickness is refused, "command not done") |

Against the fixed 1e-3: the every-edge sweep changes no result's status
and no volume; ten tolerances grow where a tangent plate is now kept (its
approximation is allowed ten times its miss -- #962's chamfer and fillet
at the arm's foot, e.g. 0.023 to 0.068 at radius 2, and #474 Fillet002
E13). The vertex sweep changes no status; 197 volumes move by under 1e-4.
The thickness suite (378, with `1e64700c94`) passes.

## The corner setback fallback (2026-10-06)

Where a fillet fails at a corner, TKFillet now computes it again with the
corner set back: the fillets there cut back along their edges and the
opening closed by one patch tangent to them, first where the fillets meet,
then 1, 1.5, 2 times the largest radius at the corner
(`ChFi3d_Builder::SetCornerSetbackFallback`, default 2, 0 = off; FreeCAD's
Part preference `FilletCornerSetbackFallback`). The design and the
measurements are fcad's `docs/CornerBlending.md`, sections 9.1 to 9.3. A
result is kept only if it is valid, valid again once written and read back,
has no edge looser than the input's loosest or a twentieth of the radius,
no face of no area, and holds every fillet asked for; otherwise the failure
is as it was.

Nothing that is made without it changes: the every-edge and vertex sweeps
are identical for every fillet made before (2680 and 9611 results). Of the
failures, 64 and 301 are made now.

| Case | What it covers |
|------|----------------|
| `issue876_corner4_r{0.3,1}` | the four edges at #876's corner, refused before (`Standard_ProgramError`, a stripe's end without a point at the far corner): made, both corners set back where the fillets meet |
| `issue876_corner4_r1_no_fallback` | the same with the preference at 0: refused, as before |
| `seam_end_top_r{2.5,3}`, `mirror_top_r{2.5,3}` | the end past the cylinder's radius, still refused as a cut over two faces: made with the end set back, at 2.5 where the fillet meets the corner, at 3 at twice the radius (nearer setbacks keep edges looser than a twentieth of it) |

Two failures had no vertex to report and now do, which the fallback needs:
a corner that keeps only a partial result, and a corner that leaves a
stripe's end without its points. A corner that puts a null shape in the DS
fails too: once the fallback mended another corner of the same fillet, the
topological build read it and the process died (`issue273_Fillet001` edges
38 and 39 at 0.3, 81 vertex-sweep cases in a first run).

## A fillet's line over a wall kept in coplanar pieces (realthunder/FreeCAD#962, 2026-10-09)

The model's rib (y 17.1..20.3) has a flat top at z=32.25 that ends, at
x=38.5, on a face sloping down (normal 0.46,0,0.89). Its side wall (y=20.3)
is two coplanar faces, split by a vertical edge at x=39.197, where the slope
has come down to z=31.886. The fillet on the top's edge along the wall:
from radius 0.364 on, its line on the wall (z=32.25-r) passes under the
slope's edge with the first piece, crosses the split, and meets the slope on
the second piece's edge. The walk stops at the spine's end with that side
still in the face; `PerformOneCorner` found no face at the end for its two
points and handed the corner to `PerformIntersectionAtEnd`, whose plate was
off by up to 0.017 at radius 0.4 to 0.7 (a chamfer 0.08, all "valid") and
invalid from 0.8 -- the second piece kept whole under the fillet, its wire
and the slope's open.

`PerformOneCorner` now carries the line on (`LineOverSplit`, file-local):
the side in the face is a plane, its line straight; carried on it crosses
one edge of the face into a piece of the same plane, the same way up, and
meets the face at the end on an edge of that piece, crossing nothing else.
The point goes on that edge, the cut is made as on a wall in one face, and
the line is stored in two: on the first piece to the split (where FILDS
ends it), on the second from the split to the cut -- the two curves and
their points put in the DS here, as for the cut over two faces. A piece
the other way round on its surface (#962's second piece is REVERSED) has
the line's transitions turned over.

The end now matches the same fillet on the shape refined (`removeSplitter`)
to 1e-7, the chamfer to 1e-13, at every radius from 0.3 to 0.95. The rest
of the difference, 0.05 at 0.8, was at the edge's other end (z=14, four
edges, the wall's line crossing the same split onto the block's top), and
from radius 1 that end failed: made in the next section.

| Case | What it covers |
|------|----------------|
| `issue962_rib_top_r{0.5,0.8,0.95}`, `issue962_rib_top_chamfer_0.8` | the rib's top edge: 0.5 off by 6e-3 before, 0.8 and 0.95 invalid (the volumes, the refined shape's to 1e-5, since the foot below) |
| `slant_split_wall{,_mirror}_r{0.8,1.5,2}` | the rib in miniature, built: a prism whose top slopes down past x=4, its front wall split at x=5; the volume taken is the fillet's cross-section swept to the slope, closed form (0.8 off by 0.028, 1.5 and 2 invalid, before) |

The fillet sweep (`sweep/`): every edge, 20 invalid results made valid --
the rib's chain at 0.8, on the Fillet's input and on the Chamfer's -- and
20 valid ones one face fewer, 1.4e-3 nearer the refined shape's volume (the
other rib's chain at 0.3, whose end the plate had made); every vertex, 4
invalid made valid and 116 the same correction. Nothing else moved, nothing
lost. The suites (fillet, draft, thickness), FreeCAD's Part and PartDesign
tests and the draft sweep are as before.

## The same line at a corner of four edges (realthunder/FreeCAD#962, 2026-10-09)

The rib's chain runs from its top down its front, tangent, and its last
edge -- the rib's wall (y=20.3) against the 45 deg underside of its
overhang -- ends at the rib's foot, (38.5,20.3,14), on the block's top
(z=14). Four edges meet there: the underside's with the block's side
(x=38.5), the side's with the top, the top's with the wall, and the
fillet's own. The fillet's end is cut by the block's top: its line on the
wall comes down to it at x=38.5+1.414r, past the wall's split (x=39.197)
from r=0.493 on; on the underside its line ends on the edge with the side.
`PerformIntersectionAtEnd` makes such an end by cutting the fillet with the
faces around the vertex, from one line's edge to the other's -- here from
the underside's edge with the side, over the side, to the top's edge with
the wall. With the wall in two pieces, that edge is two: the line ends on
the far one, which does not reach the vertex.

- From r=0.986, where the walk itself crosses the split before the end,
  the line's end on the far edge made the face search take the corner for
  a cap (`IntersectMoreCorner`, "cap not written"): the fillet failed.
- At r=0.493..0.986 the exact fillet's line was cut at the split
  (`SplitKPart`), and the walk past the end, its other side held at a point,
  stopped there too: the end was made "valid", off by up to 0.09.

Now (`ArcPastSplit`, file-local): a line ending on an edge away from the
vertex, which carries on, across the split's foot, the edge of the vertex
between the near piece and the block's top, is taken as if it ended on that
edge -- the faces at the end are the same as on a wall in one face, the
edge of the vertex left out of the search and, wholly under the fillet,
given a point at its far end that keeps nothing of it. When the line stops
in the near piece, the walk past the end is dropped and the exact line
carried over the split as at the rib's top (`LineOverSplit`; its piece on
the far piece stored by `StoreLineOverSplit`, now shared by both ends).

The end now matches the refined shape to 1e-5 at every radius from 0.3 to
3 but one (below), and the chamfer exactly from 0.3 to 0.9. Built in
miniature, both ways round, fillet and chamfer match their closed forms.

| Case | What it covers |
|------|----------------|
| `issue962_rib_foot_r{0.6,0.8,1,1.5,2.5}` | the foot: 0.6 and 0.8 off by 0.02 and 0.05 before, 1 to 2.5 failing; the refined shape's volumes, to 1e-5 |
| `rib_foot_split{,_mirror}_r{0.8,1.2,1.5,2}` | the foot in miniature, built: a rib with a 45 deg underside on a block, its wall split at x=1; the volume taken is the cross-section swept between the slope's end and the block's top, closed form (0.8 and 1.2 off by 0.05 and 0.17 before, 1.5 and 2 failing) |
| `issue962_rib_chamfer_1.2` (XFAIL) | see Known broken |

Still open at this corner: a radius within 5e-4 of 0.986 (the split
crossing the line within tolerance of the spine's end: invalid or refused,
as before); and a radius whose walk past the end must go further than half
the spine's length (`ChFi3d_FilBuilder::ExtentOneCorner`), which the
miniature reaches at 2.5 -- on the refined shape too it is the exact
fillet that carries it. (Both since: "A spine extended past a corner by
the radius" and "The split within tolerance of the line's end", below.)

The fillet sweep (`sweep/`): every edge, 60 refused made (the rib's chain
at 0.8 and 2 on the Fillet's and the Chamfer's inputs) and 20 valid ones
corrected by 0.049 to the refined volume (0.8); every vertex, 232 refused
made (the same inputs, radius 1). Nothing else moved, nothing lost. The
suites (fillet, draft, thickness), FreeCAD's Part and PartDesign tests and
the draft sweep are as before.

## A flag read before it was set (2026-10-09)

`ChFi3d_ExtendSurface` extends a face's B-spline or Bezier surface once,
and leaves it alone when the flag it is given is already set.
`IntersectMoreCorner` passed it an `int` it never initialized, so whether
the face at the fillet's end was extended -- and the corner's cut computed
on it -- was whatever the stack held; `PerformIntersectionAtEnd` zeroed
its flags only up to the last face but one, and an OnSame end reads the
last. Both start at zero now, as every other call starts them.

It showed when the change above moved #474's Fillet003 results at two
vertices by up to 0.47 without running any of its new code: the file
compiled with `-ftrivial-auto-var-init=pattern` gave the same, with
`=zero` the baseline's, and `-ftrivial-auto-var-init-stop-after` bisected
it to the one variable.

| Case | What it covers |
|------|----------------|
| `issue474_f003_e51_r{0.3,0.8}` | #474's Fillet003 input, edge 51 (the vertical at x=6.415, y=11.307), whose foot is four edges on a B-spline face: refused at every radius before; the material taken is the cross-section times the edge's length to 0.1% |

In the sweep, edge 51 at 0.3 and 0.8 and 10 vertex cases with it, made;
nothing else moved.

## A corner's curve kept on its face (realthunder/FreeCAD#523, 2026-10-10)

The bottoms at radius 2 of "An end point a rounding error past the line",
above. The corner's curve on the cylinder ends at the far vertex, tangent
to the circle the bottom cuts there, and leaves it at fourth order
(z = x^4/64). Its pcurve, degree 7 with 38 poles, has its last pole on the
circle's line (v = 0, v = -z) and the one before 1.1e-6 past it, so the
curve runs up to 1.6e-9 past the face over its last 1% -- where BRepCheck
found the wire crossing itself. The tops' curves do the same (the
crossing found there or not by chance).

Putting the curve on the face's side is not enough. The true curve lies
within 1e-10 of the circle for 0.009 from the vertex, so a curve that only
keeps to its side still touches the circle as BRepCheck's 2D intersection
(1e-10) sees it, farther from the vertex than the vertex's tolerance
(1.3e-7) and where the circle's sag is too much for its excuse along the
chord. The curve has to leave the circle at an angle.

`KeepCurveOnFace` (`PerformOneCorner`, on the curve on Fv and on FvT): a
B-spline curve whose end lies on an iso-line bounding the face, not a
periodic one, with poles past it, is refined towards that end with simple
knots until its poles close in on the curve; the poles past the line go
onto it, and the one next to the end 1e-8 inside. Within the hull of its
poles, the curve is then inside the face but at its end, and leaves the
line at an angle: any touch the intersection finds lies within the chord's
excuse. The refinement that moves the curve least is taken, once within
twice the margin; never one moving it more than `Precision::Confusion()`,
and the move is added to the curve's tolerance. Here it is the margin,
1e-8; the tops are kept on their face as well.

A first try made the end span a Bezier piece (one knot of full
multiplicity) and clamped its poles: the bottoms were valid, but the
pcurve was only C0 at the knot and #876's Fillet002 edges came out at
3.9e-4 for 1e-4 (the suite's cap is 2e-4), the curve moved by 2e-11. With
simple knots the curve keeps its continuity and those tolerances stay.

Still open: at radius 2 all four results, tops and bottoms, before and
after, have two vertices at the far vertex's point, 4e-15 apart -- the
fillet's line on the top (bottom) ends at the cylinder's far vertex and the
corner makes a new vertex there. BRepCheck lets it be; BOP's argument check
reports it (vertex self-interference). The vertex is a pinch: at radius 2
the top (bottom) is the box's face beyond the fillet's line and the
cylinder's whole disc -- the cap takes the cylinder round past 2 pi -- and
the line is tangent to the circle at that point, so the face is two
regions touching at one point, its one wire through the point twice.
Taking the existing vertex for the end in the OnSame update (with the
three sites in `PerformOneCorner` that read the end as a DS point told it
is a vertex) builds just that, and BRepCheck finds the face unorientable
(`BadOrientationOfSubshape` on its wire); the 4e-15 between the two
vertices is what lets it pass now. The right shape is two faces sharing
the vertex, which means splitting the rebuilt face, its history with it;
not taken, for a case at exactly the cylinder's radius.

| Case | What it covers |
|------|----------------|
| `seam_end_bottom_r2`, `mirror_bottom_r2` | valid, at the tops' volume 1087.3009 (XFAIL before) |

The sweeps: edge, the two bottoms BAD -> ok and nothing else changes
status; vertex, no status changes. No tolerance moves by a factor of two.
Volumes move on #273's and #962's shapes, by up to 1.9e-3 (1.6e-7 of
them): GProp's default integration, which the curves' added knots move --
at 1e-10 the old and new results of #962's E20 and E21 at radius 2 agree to
the sixth decimal (11580.489655, 11581.563369).

## A spine extended past a corner by the radius (2026-10-10)

`ExtentOneCorner` extends a fillet's spine past an end at a corner by half
its length, for the walk to run on past the vertex and the corner to cut
it back. On an edge short for its radius that is not far enough: the rib
foot in miniature (`rib_foot`, the edge 4.24 long) needs the wall's line
carried over the split to the block's top, which takes the walk past the
vertex by the radius -- from 2.25 on, more than 2.12, and the corner at
the foot was refused (`ChFi3d_cherche_edge`). The refined shape, whose
line needs no walk past the split, is made up to 2.8; at 3 the
underside's line is on its far edge and neither starts.

Extending every such spine by 1.5 radius, as `ExtentTwoCorner` does,
makes these, but moves results made before: the sweep lost four #876
vertex cases and moved #876's E50 at 2 by 0.24 and #474 Fillet002's V1
pair by 0.47. So it is a fallback, `ComputeLongExtension`: when the
computation has failed and the setback fallback found nothing, and a
fillet stripe has an end at a corner with half its length under 1.5
radius, the computation is tried again with those ends extended 1.5
radius (`ChFi3d_LongSpineExtension()`, read by `ExtentOneCorner`); failing
at a vertex, with the setback fallback over that. The result is kept on
the setback fallback's terms (valid, valid read back, every fillet made, no
edge looser than the input's or a twentieth of the radius); otherwise the
computation as it was, its failure with it. Nothing made before changes.

| Case | What it covers |
|------|----------------|
| `rib_foot_split{,_mirror}_r{2.3,2.5,2.8}` | refused before; the closed form's volume |

The sweeps: edge, nothing moves; vertex, 20 EXC -> ok and nothing else --
#876's Fillet and Fillet001 at radius 1, edges 42 and 53 (71 and 83),
2.5 long, alone and with a neighbour, made with the longer extension and
the corner set back.

## The split within tolerance of the line's end (realthunder/FreeCAD#962, 2026-10-10)

#962's rib foot where the wall's line at the spine's end meets the split,
r = 0.98571 (x = 38.5 + 0.7071 r = 39.197). Measured against the refined
shape: from 0.9852 to 0.9858 the end was made 0.09 off (the old error, the
line cut at the split), at 0.986 invalid, 0.9862 refused, 0.9865 and
0.9868 invalid; 0.985 and 0.987 right.

Below the coincidence the walk past the end stops on the split 6.6e-4 or
less past the line's end, and `LineOverSplit` looked for the crossing only
from 2e-3 (twice its tolerance) past that end: it found none, and the old
path cut the line at the split. At 0.986 the crossing is 1.6e-4 before the
end -- the walk reached the split without seeing it -- and was not looked
for either. Now the search starts 2e-3 before the end: the line is
straight, and cut where the split crosses it within the tolerance of its
end, on either side, it runs on over the far piece as it does beyond. It
still takes exactly one crossing, so nothing else is taken by it. 0.9852
to 0.986 match the refined shape to 2e-6.

Still open: 0.9862 to 0.9868. There the walk crosses the split 1e-3 or less
before the spine's end and leaves a piece on the far face 3e-4 to 6e-4
long, which stops at the spine's end instead of running on into the
extension as it does from 0.9869 (to the block's top's edge); the corner
then has nothing at the end to cut. The stop is decided in the walk's
targeting (`PerformSetOfSurfOnElSpine`), not by its end test; not taken
further for a window 6e-4 wide. (Closed in the next section -- and the stop
was not in the targeting.)

| Case | What it covers |
|------|----------------|
| `issue962_rib_foot_r{0.9855,0.986}` | the refined shape's volume to 1e-5 (0.09 off, invalid before) |

The sweeps (edge, vertex) and the draft sweep: nothing moves.

## A split a sliver inside the line's end (realthunder/FreeCAD#962, 2026-10-10)

The window left open above, #962's rib foot at r 0.9862 to 0.9868, was not
a stop in the walk's targeting. The exact fillet along the foot's edge is
cut where its line on the wall meets the split (`SplitKPart`), and there
the cut falls inside the edge, 4.4e-5 (0.9862) to 6.4e-4 (0.9868) from its
end: a sliver of the exact fillet, then a walk from the cut back past the
end. The underside's line leaves its face exactly at the end (on the block's
top), and the walk starts 3e-5 to 4.5e-4 from that edge:

- 0.9862, 0.9863: no first step lands with both lines in their faces before
  the step falls under the guide's tolerance -- refused.
- 0.9865 to 0.9868: the walk reaches the underside's edge and is continued
  past it, the underside unclassified, at the largest step `ComputeData`
  allowed for the sliver -- a fifth of it, 1.3e-4. The continuation's strict
  2D check calls a step under 1e-4 in both u and v the same point, and the
  walk stops at once: invalid. From 0.9869 the step is 1.5e-4 and the walk
  goes on, 6600 sections to the block's top -- right, by a hair.

Now `SplitKPart`, at the spine's end, does not cut a line at a split of its
wall (the face across the edge a coplanar piece, the same way up) when the
cut is within 10 tolapp3d of where the other line's piece ends: the line
runs on over the split, as where the split is past the end, and the end
carries it over the split (`LineOverSplit`, which looks for the crossing
within that of the end, on either side). 0.9862 to 0.9868 then go as 0.9861
does; every radius tried from 0.985 to 1 matches the refined shape to 3e-6.

Tried and dropped: continuing the walk at the stripe's largest step rather
than the sliver's. It made 0.9865 to 0.9868 as well, but moved #962's other
rib at 0.3 -- `issue962_Fillet` E111/E113, `issue962_Chamfer` E100/E102 --
0.0031 off the refined shape (3e-5 before), its tolerance 1e-4 -> 1.6e-4.

| Case | What it covers |
|------|----------------|
| `issue962_rib_foot_r{0.9862,0.9865,0.9868}` | the refined shape's volume to 1e-5 (refused, invalid, invalid before) |

The sweeps (edge, vertex): nothing moves.

## A face that is two regions touching at a point (realthunder/FreeCAD#523, 2026-10-10)

The duplicate vertex left open in "A corner's curve kept on its face": at
radius 2 the top (bottom) of #523's box and cylinder is the box's rectangle
and the cylinder's whole disc, touching only at the cylinder's far vertex,
where the fillet's line is tangent to the circle; the corner made a vertex
of its own there, 4e-15 from the input's, and the face's one wire passed
through the point twice, once at each. BRepCheck took it, BOP's argument
check reported both vertices self-intersecting, and one vertex in that wire
is unorientable.

`ChFi3d_SplitPinchedFaces` now touches the result after the topological
build. A face qualifies when its one wire passes a point twice, at two
vertices with no edge between them, one of them the input's; at one point
of the face's parameters (on a closed surface the wire can pass a point
twice a period apart, as at a seam -- #523's cylinder face does, and is not
split); and when each loop of the wire from there bounds a region (a loop
round a hole touching the outer one does not). For those, and only those,
the corner's vertex is replaced by the input's everywhere (the edges at it
keep their parameters), and the face is split into one face per loop. The
builder's history -- the split lists `BRepFilletAPI` reads for Modified, and
the new faces Generated reads -- is mapped onto the result in place, a split
face to its pieces; no class changes size (FreeCAD holds the API objects by
value).

A first version merged the vertices wherever a face held such a pair and
split only where it could: it turned #474's Fillet003 E18 (r 0.8, 2 and three
vertex cases at 1) from BAD to ok -- BRepCheck no longer saw the
self-intersecting wire, but BOP's check still found vertex and edge
self-intersections, at tolerances up to 1.28. Not a fix; the merge now
waits for a face to split.

| Case | What it covers |
|------|----------------|
| `seam_end_{top,bottom}_r2`, `mirror_{top,bottom}_r2` | now with BOP's check (`bop=True`): the top (bottom) in two faces sharing the vertex |
| `pinch_top_r2` | the same as the picture's case |

The sweeps: edge, the four #523 r=2 results 8 -> 9 faces at the same volume,
nothing else; vertex, nothing moves.

## A corner of five edges, two of them in line (realthunder/FreeCAD#962, 2026-10-11)

The sweep's invalid results, each tried again on the shape refined
(`removeSplitter`): 40 on single edges, 32 of them invalid on the refined
shape as well -- upstream's behaviour on that geometry, see the sweep's
README -- and 8 only on the shape in pieces. Six of the eight are #962's.

Five are one corner: (38.5,10.2,-3.75) and its twin at y=27.2, where the
arm's top meets the block's wall. The block's side (y=10.2) and the arm's
foot below the top are one plane in two faces, split along the top's level;
the edge up the wall and the edge down the arm's slanting side are one line,
on either side of the two. Five edges; on the refined shape four, two of
them in line, which `PerformIntersectionAtEnd` knows: "if two consecutive
edges are G1 there is only one face of intersection" -- the fillet cuts the
face that is not between the two, and the face between them takes only the
piece of that line from the vertex to the fillet's end.

In pieces, each of the three faces at the end was cut for itself. The
fillet's section in the pieces' plane came out twice, there and back -- on
the lower piece from the line up the wall down to the top's level, on the
upper one back again -- the lower piece's wire crossed itself, and the
fillet's face carried a tongue of no area: "Self-intersecting wire" at 0.8
on the wall's edge (fillet and chamfer), at 0.8 and 2 on the slanting
side's. At the other radii of the sweep the end failed outright and the
corner setback fallback made it, valid, at tolerances of 0.007 to 0.12.

Now the rule holds for the pieces: when the faces at the end past the first
(or before the last) are coplanar pieces, the same way up, and the edges on
either side of them are in line at the vertex (within 0.01 rad, the rule's
own measure), the fillet cuts the remaining face only. The piece that the
line's own edge borders takes the edge from the vertex to the line's end --
its pcurve there a projection, the piece a plane; the pieces between and
their splits stay as they are.

| Case | What it covers |
|------|----------------|
| `issue962_top_wall_r{0.3,0.8,2}` | the top against the block's wall, ending at that corner at both ends: the refined shape's volume to 1e-5, no tolerance above 1e-4, BOP's check (invalid at 0.8 before; 0.3 and 2 by the fallback, tolerances 0.018 and 0.12) |
| `issue962_top_slant_r{0.8,2}` | the top's edge with the slanting side, edge 33 (invalid before); `issue962_e33_r{0.1,0.3}` above are made exactly now, too |
| `issue962_top_wall_chamfer_{0.8,2}` | a chamfer on the wall's edge (invalid before, at every size) |
| `ledge_wall{,_mirror}_r{0.3,0.8,2}`, `ledge_wall_chamfer{,_mirror}_{0.5,1}` | the corner in miniature, built: a block on a base whose outline turns at the block's corner. The fillet runs on past the wall's end to the base's slanting side: the closed form's volume |
| `ledge_slant{,_mirror}_r{0.3,0.8,2}` | the base's top against its slanting side: the cross-section over the edge's length |

The sweeps: edge, the 6 invalid results valid, 12 results of the fallback
now made exactly (the tolerances above down to 1e-5, the volumes moving to
the refined shape's, by up to 0.14); #309's edge 8 at 0.3 and 0.8, the same
corner on another shape, one face fewer at the same volume -- a plate of
0.038, 0.013 out of flat, where the corner's face is now the plane itself.
## A long edge crossed close to the corner (realthunder/FreeCAD#474, 2026-10-11)

The seventh: #474's Fillet002 input, the vertical edge at (-5.494, 11.782)
from z=13 down, at 0.3 -- invalid, 707 of volume too much. Its top is a
vertex of five edges where two faces of the helical ramp meet in an edge
that winds 82 round the axis (16 turns of it). The fillet crosses that edge
0.07 to 0.4 from the vertex (r 0.1 to 0.5), and `PerformIntersectionAtEnd`
looked for the crossing by intersecting the edge's whole curve with the
fillet: the curve is sampled for that, 82 of it too coarsely to show a
crossing in its first half unit. Without the point the edge was taken for
one the fillet misses: the two ramp faces were intersected anew, and the
piece of their line from the vertex to the fillet laid on top of the edge,
which stayed whole.

On the refined shape that was a spike -- both faces ran up the new piece and
down the old edge -- valid for BRepCheck from 0.3, self-intersecting for
BOP's check, invalid at 0.1 and 0.2: the "refined is valid" of the triage
was BRepCheck's alone. On the shape in pieces (the edge under the fillet two
edges in line, the wall beside it split) the piece kept of the new line was
the wrong one: the vertex was located on it by the first extremum
`Extrema_ExtPC` returned, which on a curve winding round an axis can be a
turn away -- here 5 up -- and the rest of the curve, 81 long, was kept.

Two changes. When the whole curve shows no crossing, the intersection is
tried again on the piece of it within ten times the fillet's width of the
vertex; the edge is then cut where the fillet crosses it, as any edge is.
And where a piece of a curve is added from the vertex, the vertex is at the
nearest of the curve's points, not the first found. With the first change
nothing in the suite or the sweeps reaches the second any more.

| Case | What it covers |
|------|----------------|
| `issue474_f002_ramp_end_r{0.1,0.3,0.5}` | the edge (`models/issue474_fillet002_base.brep`): valid, BOP's check, the refined shape's volume (0.1: invalid on both shapes before; 0.3 and 0.5: invalid, 707 too much, and on the refined shape the spike) |

## The closing edge of a corner over a split (realthunder/FreeCAD#962, 2026-10-11)

The eighth: the mouth of the hexagonal pocket in #962's block, its edge at
x=38.8 on the block's side (y=10.2), 0.3 from the split of that side at
x=38.5 (the block's piece and the rib's above it, one plane). At 0.8 the
fillet's line on the side lies on the rib's piece, 0.5 past the split. The
corner at either end is `PerformOneCorner`'s, OnSame: the pocket's next wall
cuts the fillet, and the edge between that wall and the side is carried on
from the corner to the line's end -- the extension, which closes the
fillet's end. It starts in the block's piece, where the pocket is, and
crosses the split on its way. It was put on the line's face whole: the
rib's piece got an open wire of three edges, the block's piece kept the
split entire and lost nothing, "Unorientable shape".

Now, when the edge carried on belongs to a coplanar piece beside the line's
face, the extension is looked at against the edges of both
(`ExtensionOverSplit`): if it crosses one edge of the two, inside it, and no
other, it is stored in two parts, each on its piece, and the split is cut
at the crossing -- of its two sides there the one the spine leaves the
corner toward is under the fillet. The parts keep the tolerance the
extension really has (1e-7 for two planes) rather than the 1e-4 asked of
the intersection: the corner's cut leaves the line's end tangent to the
wall, and runs within d^2/2r of the first part where the crossing is d from
the end -- with both at 1e-4 BOP's check called that a self-intersection up
to d = 8e-3.

| Case | What it covers |
|------|----------------|
| `issue962_hex_mouth_r{0.5,0.8,1.2}` | the pocket's mouth: the refined shape's volume to 1e-5, BOP's check (invalid from 0.301 before) |
| `pocket_by_split{,_mirror}_r{0.3005,0.303,0.5,0.8,1.2}`, `pocket_by_split_chamfer{,_mirror}_0.5` | the mouth in miniature, built: a box whose front is split at x=5, a pocket in it 0.3 from the split. The cross-section over the edge's 4 (invalid before, 25 or 6 of volume off) |

## A fillet as wide as its piece, once more (realthunder/FreeCAD#962, #309, 2026-10-11)

"A fillet as wide as the piece of a split wall" (2026-10-03) made the walk
take a point on the split for a point of the far piece. Three things were
left of it, found on the pocket's mouth at 0.3, where the line runs along
the split, and on #309, a body all in strips 2 wide.

- The split was not seen on faces REVERSED in the shell. The walk's domain
  holds its face FORWARD, and `ChFi3d_SplitPieceOfSpine` asked whether that
  face and the one across the edge, as the shell has it, are tangent --
  which `ChFi3d::IsTangentFaces` denies of two faces REVERSED in the shell
  when one of them is turned. A box made by `Part.makeBox` has its bottom,
  front and left that way: the miniatures of 2026-10-03 happened to stand
  on the other three. The face is now taken as the shell has it. The
  mouth at 0.3 and the strip box at 2 were refused on the box as built and
  made (or made wrong) on its mirror image.
- The extension ending on the split: with the line along the split, the
  extension lies in the spine's piece whole and meets the split at its end.
  It is stored there, and the split cut at the line's end
  (`ExtensionOverSplit`, at end). The same where the crossing is so close
  to the end that the corner's cut passes it within the parts' tolerance
  (to d = 3e-4 at radius 0.3): the line's end and the split's are then one
  vertex, of tolerance d.
- A line's end on a vertex, by an edge that is not the corner's. Where the
  end face is in pieces too, the walk on the far piece ends at the split's
  end vertex on that piece's own edge with the end face's far piece, and
  `FindFace` found no face holding both sides' edges: the corner went to
  `PerformIntersectionAtEnd`, which cut the near end piece and left its
  edge under the fillet in place -- invalid, 12 too much on the strip box,
  1600 on #309. The side's end is now put on the corner's own edge to that
  vertex, at its far end, nothing of it kept; the corner is then the one
  the unsplit end face has, and the split under the line goes with its
  piece as before.

- A stripe that stops short. With the split seen, #309's edge 3 at 2 -- a
  circle's arc and, tangent to it, a 2-long edge down the body's end, the
  faces beside both 2 wide -- could start its walk, on the short edge's far
  piece, and ended it at the vertex between the two edges: the next edge's
  face, the cylinder's strip, as wide as the fillet with a sharp edge
  beyond, gives it no line. `PerformSetOfSurfOnElSpine` takes a walk on a
  guide that reaches the spine's end for finished wherever it stops, and
  the corner at the arc's far end, 56 away, was made of that surface. As
  long as the corner at the near end failed, the fillet was refused; with
  the third change it came out invalid, a face of tolerance 30.
  `PerformSetOfSurf` now refuses a stripe whose surfaces stop short of an
  end of its spine by more than ten times their width there and more than
  half the spine's edge they stop on (an end face on a slant stops them a
  width or two before the vertex). The refined shape refuses that fillet
  as well: its radius is the width of the cylinder's strip.

| Case | What it covers |
|------|----------------|
| `issue962_hex_mouth_r0.3` | the line along the split: the refined shape's volume (refused before) |
| `pocket_by_split{,_mirror}_r{0.3,0.30005,0.3003}` | the same in miniature, to 3e-4 past the split: the closed form, BOP's check, the end vertices' tolerance under 1e-3 (refused or invalid before) |
| `strip_box{,_mirror}_r{2,2.00005,2.0001}`, `strip_box{,_mirror}_chamfer_2` | a box whose bottom is split 2 from its edge and whose end faces are split there too: the cross-section over the edge's 10 (refused, or invalid with 12 too much) |
| `strip_box_plain_ends{,_mirror}_r{2,2.00005,2.0001,2.001,2.5}`, `..._chamfer_2` | the same with the end faces whole (2 and 2.00005 refused on the box as built) |
| `issue309_e17_r2` | #309's edge 17 at the width of its strips: the refined shape's volume (refused before) |
| `strip_box{,_mirror}_r2.5` | refused then; made since, see "A corner's cut over an end face in two pieces" |

The sweeps, the four sections together. Edge: the 8 results invalid only
in pieces are valid; 2 refused are made (#962's pocket mouth at 0.3, #309's
edge 17 at 2); 12 results of the corner setback fallback at #962's corner
are made exactly, their tolerances from 0.007..0.12 down to 1e-5, their
volumes moving to the refined shape's by up to 0.14; #309's edge 8 has a
face fewer at the same volume, a plate of 0.038 that was 0.013 out of flat
now the plane itself; nothing else moves. 2519 valid, 32 invalid -- on the
refined shape as well, all 32 -- and 1370 refused. Vertex: 7 invalid
results valid and 2 refused made, the same edges alone at their ends; 106
valid results at the corners of five edges of #962 and #309 made exactly,
as on the edges; and 6 from refused to invalid -- the pocket mouth's edge
together with the mouth's next edge or the pocket's corner edge, at 0.3.
Two stripes meet at the pocket's corner there, one with its line on the
far piece of the side, and the corner of two does not take them for
sharing a face: at 1 those cases were invalid before as well; at 0.3 the
split was not seen and the fillet refused before it came to that. The
refined shape makes them all. Open, with the rest of the vertex sweep's
invalid results (290).

## Two fillets of opposite concavity where a split ends (2026-10-12)

The vertex sweep's invalid results, each tried again on the shape refined
(`sweep/triage.py`): 290, of them 181 invalid there as well, 23 on a split
itself, and 86 invalid only in pieces -- all of them two or three edges
filleted together. 55 of the 86 are one corner: two edges at a vertex where
a split of a wall kept in coplanar pieces ends, the one concave and the
other convex. A slot's floor edge with its wall's edge on the outer face,
the outer face split below the floor; the concave edge between a fin and
its block with either edge of the L-shaped side they share; on #962, the
corners where the arm meets the block.

The corner of two fillets of opposite concavity (`PerformTwoCorner`) is a
three-sided patch: a section of the one fillet (`OnSame`), a section of the
other (`OnDiff`), and an edge in the plane of the face across the first --
from that fillet's line on the face to the point where the second ends on
an edge of it. With that face in two pieces, the split between them ending
at the vertex, the edge the second fillet ends on bounds the other piece.
The patch's edge was put on the first piece alone: the piece did not close
("Self-intersecting wire", or an open wire), the edge the second fillet
cut was cut for one of its two faces, and the first fillet's spine was
left in the piece's outline. Up to 300 of volume off.

Two cases, by where the patch's edge runs:

- **Past the split, outside both pieces.** The wall has a reflex corner at
  the vertex -- 270 degrees on the slot -- and the edge crosses what the
  fillets take away or add. On the wall in one face the cut edge's piece
  from the vertex is gone, the face closing along the patch. In pieces
  that piece of the edge stays, an edge between the two: the first piece
  closes along the patch, that edge and the split, and the other keeps its
  outline. The vertex stays, and the first fillet's spine, an edge of the
  first piece, is removed from it.
- **Across the split** (the arm meets the block at 137 degrees, their tops
  and bottoms two pieces each): the patch's edge is cut where it crosses, a
  part on each piece -- two edges of the patch -- and the split is cut
  there, its piece from the vertex gone with the vertex.

An edge through an end of the split, or crossing it twice, is refused.

| Case | What it covers |
|------|----------------|
| `slot_split_outer_floor_and_wall_r{0.3,1}`, `slot_split_outer_floor_and_end_r{0.3,1}` | the slotted block, its outer face split below the floor: the floor's concave edge with the wall's edge on the outer face, and with the floor's -- the refined shape's volume to 1e-3, no tolerance above 1e-3, BOP's check (invalid before, at every radius) |
| `fin_on_block_x{0,10}_top_and_inner_r{0.3,1}`, `fin_on_block_x{0,10}_inner_and_upright_r{0.3,1}` | the fin flush with its block's side, the side an L in two faces: the concave edge between them with the block's top edge and with the fin's upright edge, at either side (invalid before, 51 of volume too much on the first) |
| `arm_on_block_z{-9.75,-3.75}_upright_and_block_r{0.3,1}`, `..._upright_and_arm_r{0.3,1}` | the arm on the block, the edge crossing the split: the upright edge where they meet with the block's edge and with the arm's, top and bottom (invalid before). The corner's filling depends on the way its face's surface is parametrized, on the refined shape too -- its two ends, mirror images, differ by 4.4e-3 at radius 1: the volume to 1e-2 there |

The picture cases: `slot_split_outer_floor_and_wall_r1`,
`arm_on_block_z-3.75_upright_and_block_r1`.

## Two fillets on the two pieces of a wall (2026-10-12)

10 more: the two convex edges at the inner corner of an L-shaped wall made
of two faces, the split ending at the corner -- the fin flush with its
block's side; two pads side by side, the second shorter. Each fillet has
one of the pieces for its face. They have no face in common,
`PerformTwoCorner` found none (`ChFi3d_IsInFront`) and made the corner a
plate (`PerformMoreThreeCorner`), which came out inside out: invalid, 0.35
of volume too much on the fin at radius 0.3, 1.1 at 1.

On the wall in one face the two fillets' lines on it meet past the corner,
on one of the pieces, and the fillets are cut by one another, along the
curve from there to the corner's concave edge
(`PerformTwoCornerbyInter`). The same is done now. The line of the one
fillet stops on the split; while the two are intersected it has the
other's piece for its face and is carried on past the meeting point, as it
runs on the wall in one face. Then it ends on the split again, and its
piece from there to the meeting point is put on the other piece and on its
own fillet (`StoreLineOverSplit`, which does the same for one fillet's
line over a split wall); the split is cut where the line crosses it.

Done where both fillets end `OnSame`, at one point of one edge on their
other sides; the two pieces lie the same way round on their surface; the
two lines are straight; and the fillet that stops on the split is a
cylinder or a plane, a surface that goes on past its end as it is. 7 of
the 10. Two of the others are #962's corner at a circle's edge; the third
has a fillet that is walked there (a B-spline), left to the plate as
before (`fin_on_block_wall_top_and_upright_r1`, see Known broken).

Made as well: the slot's wall edge and floor edge on the outer face, both
on its pieces (`slot_split_outer_wall_and_end`) -- refused before.

| Case | What it covers |
|------|----------------|
| `fin_on_block_x{0,10}_top_and_upright_r{0.3,1}` | the block's top edge and the fin's upright edge at the L's inner corner, at either side: the refined shape's volume to 1e-6, tolerance 6e-7 (invalid before) |
| `fin_on_block_wall_top_and_upright_r0.3` | the same with the fin's wall split 0.7 from the side as well (invalid before) |
| `slot_split_outer_wall_and_end_r{0.3,1}` | the slot's two edges on the outer face in pieces (refused before) |
| `fin_on_block_wall_top_and_upright_r1` | XFAIL then, a plate inside out; made since, see "The far piece's fillet at an end OnSame" |

The picture case: `fin_on_block_x10_top_and_upright_r1`.

## A corner that read another fillet's surfaces (2026-10-12)

`PerformMoreSurfdata` makes the corner at an end where the face the fillet
ends on holds two of the fillet's surfaces -- a fillet whose line crosses a
split of its face just before the end. It took the face of the
neighbouring surface from `myListStripe.First()`, the first fillet made,
not from the corner's own. With one fillet they are the same; upstream's,
never met with one face per wall.

With two edges filleted, the second ending that way, the corner was made
on a face of the first fillet. On the arm fused to a block, the block's
upright edge and then its bottom edge to the arm: valid, with 3.6e-3 of
volume too much at radius 0.3 and 0.13 at 1, the fillet's end a round nose
on the block's bottom where it runs out on the arm's. On the sweep's
shapes: invalid, a face of tolerance 21 (6 of the 86).

| Case | What it covers |
|------|----------------|
| `arm_on_block_corner_upright_and_bottom_r{0.3,1}` | the block's far corner, the upright edge first: the refined shape's volume to 1e-3 (valid, 3.6e-3 and 0.13 too large before) |

The picture case: `arm_on_block_corner_upright_and_bottom_r1`.

## An intersection curve a turn away on a closed surface (2026-10-12)

One of the 86, and a result the sweep took for valid. Two top edges at the
arm's far end: the second fillet is walked -- its line on the top crosses
the split -- and cuts the first, a cylinder, in a curve that starts on the
cylinder's seam. `ChFi3d_ComputeCurves` takes the first line of
`GeomInt_IntSS` whose ends are the expected ones, however far it lies from
the surfaces. Here the line's pcurve on the cylinder started at 2 pi where
the curve starts at 0, and ran straight from there to its other end,
across three quarters of the cylinder; it was moved to its expected start
and kept. The edge lay 2.8 off its surfaces at radius 1 (invalid) and 0.9
at 0.3 -- valid for BRepCheck, which measures no edge against its
tolerance's size, not for BOP's check.

A line more than ten times the tolerance off is now kept aside and the
path walked (`IntWalk_PWalking`, as where `GeomInt` finds no line); the
closest of them is kept.

| Case | What it covers |
|------|----------------|
| `arm_on_block_far_top_edges_r{0.3,1}` | the arm's two top edges at its far end: the refined shape's volume, no tolerance above 1e-3, BOP's check (tolerance 0.9 and 2.8 before, the second invalid) |

The picture case: `arm_on_block_far_top_edges_r1`.

The sweeps, the four sections together. Edge: no result changes its
state and no valid one moves (nine invalid ones of #273, invalid on the
refined shape as well, have another volume -- the intersection line).
Vertex: 69 invalid results valid, at the refined shape's volume -- 55 the
corner of opposite concavity, 7 the two pieces of a wall, 6 the corner
that read another fillet, 1 the intersection line; 3 refused results made,
the slot's two edges on its outer face in pieces; and 76 valid results
moved. 12 of those were made on the wrong fillet's face, 0.13 of volume
too much at radius 1; 8 were plates, between two fillets on two pieces,
and are exact now, a face fewer, their tolerance down from 1e-3..4e-3
to under 3e-5;
56 have an intersection line walked again, on the issues' own shapes as
well (#273, #474, #631) -- where that edge held the largest tolerance, it
is down from 1e-3..6e-3 to about 1e-4, and one of #631's no longer fails
BOP's check. Nothing worse: 9190 valid, 221 invalid, 2831 refused.

Of the 86, 17 are left: 12 at the two corners of the hexagonal pocket's
mouth on #962, where the mouth's edge has its fillet's line along the
split of the block's side; 2 at #962's corner on a circle's edge; 2 at
a vertex of four sharp edges on #309; and the fin's wall split, at radius
1 (Known broken).

## A fillet's line along a split, at a corner of several fillets (realthunder/FreeCAD#962, 2026-10-12)

The 12 at the pocket's mouth, in four parts; this one is the six at radius
0.3. The mouth's edge at x=38.8 is 0.3 from the split of the block's side
at x=38.5, and at 0.3 its fillet's line lies on the far piece, along the
split: the strip between edge and split goes under the fillet ("A fillet
as wide as the piece of a split wall", above). At either end of that edge
are the mouth's next edge and the pocket's inner edge. With any of their
fillets the corner is made on the faces at the vertex, and the far piece
is not one of them:

- with the mouth's next edge, whose fillet runs on the near piece, the
  two fillets had no face in common and the corner was a plate, inside
  out (invalid, 119 of volume short);
- with the inner edge, of opposite concavity, and with both, the plate's
  edge on the wall ended on the split and neither piece was closed along
  it.

Fix `fbff94bd8b`: while a corner of two fillets or more is made, such a
line is shown on the spine's piece -- the face the near piece, the line's
curve on it the projected one, its transition turned where the two pieces
lie the other way up on their surfaces (`LineOnSplit`, in
`PerformFilletOnVertex`). After the corner it is put back on its own
piece, and the split is cut where the line now ends, its part under the
line gone. The corner is then the one the wall in one face has: the two
mouth fillets cut by one another (`PerformTwoCornerbyInter`), the three
fillets' corner (`PerformThreeCorner`).

| Case | What it covers |
|------|----------------|
| `issue962_hex_mouth_{top,bottom}_mouth_and_side_r0.3` | the mouth's edge beside the split and the next: the refined shape's volume to 1e-7, tolerance 1e-4, BOP's check (invalid before) |
| `issue962_hex_mouth_{top,bottom}_all_three_r0.3` | with the inner edge as well (invalid before) |
| `issue962_hex_mouth_{top,bottom}_mouth_and_inner_r0.3` | the mouth's edge and the inner edge (invalid before; see the corner without a pivot, below) |
| `pocket_by_split{,_mirror}_corner_{mouth_and_side,mouth_and_inner,all_three}_r0.3` | the same on the miniature, a rectangular pocket 0.3 from the split of a box's front, as built and mirrored (invalid, the pair with the inner edge refused) |

The picture case: `issue962_hex_mouth_top_mouth_and_side_r0.3`.

## Two fillets on two pieces of a wall, the split beside the vertex (realthunder/FreeCAD#962, 2026-10-12)

The mouth's two edges at radius 1. The fillet of the edge beside the split
has its line 0.7 inside the far piece; the fillet of the next runs on the
near piece, and its line comes to the split. On the hexagon it crosses
the split 0.23 before the vertex and ends in two surfaces, the last on the
far piece: the two fillets have that piece in common, a face the vertex
is not on. `ChFi3d_IsInFront` asked for the vertex's parameters on the
common face (to choose among several meeting points) with
`BRep_Tool::Parameters`, which throws there -- refused. On the rectangular
miniature the line reaches the split 0.3 past the vertex: no face in
common, a plate, invalid.

Fix `6593a88daa`. The vertex is projected on the common face's surface where
the face does not hold it. And "Two fillets on the two pieces of a wall"
(above), made for a split that ends at the vertex, takes one that passes
it by: the split is looked for among the two faces' edges; neither line
being on the split, the line carried over it is the one whose meeting
point with the other lies in the other's piece, and where it crosses the
split is computed; the pieces may lie the other way up on their surfaces;
and the other fillet's line may be a walked one, a B-spline, straight all
the same.

`PerformTwoCorner` also searches the surfaces before the last for a common
face, and ran into the same exception there. That search is kept from a
face off the vertex by a refusal of its own: the corner it makes of such a
surface is a plate from where the surface ends, valid and 0.19 of volume
off on the slot's miniature (its floor edge and outer wall edge at 1).

| Case | What it covers |
|------|----------------|
| `issue962_hex_mouth_{top,bottom}_mouth_and_side_r1` | the hexagon's two edges: the refined shape's volume to 1e-5, tolerance 1e-4, BOP's check (refused before) |
| `pocket_by_split{,_mirror}_corner_mouth_and_side_r1` | the rectangle's: the two cylinders cut by one another, the refined shape's volume to 1e-6 (invalid before, 1.2 of volume short) |

The picture case: `pocket_by_split_corner_mouth_and_side_r1`.

## Two fillets of opposite concavity without a pivot (realthunder/FreeCAD#962, 2026-10-12)

Either of the mouth's edges with the pocket's inner edge, at radius 1:
four of the 12. `PerformTwoCorner` looked first for the pivot -- the edge
both fillets end on, away from their common face -- and made a plate when
the first fillet's point there was not on an edge. The corner of opposite
concavity has no use for a pivot: it is made of the fillet `OnSame` cut
where the two lines meet on the common face, and of the edge the fillet
`OnDiff` ends on. On a wall in one face the first fillet's line reaches
the face's far edge, however far, and passes for having a pivot; a line
that stops in its face did not -- a walked fillet's, carried past the
vertex inside the face, and one stopped by a split. The plate's edge on
the wall then ended on the split or crossed it, and both pieces were left
open.

Fix `3f7ddd4bcc`, in three parts:

- No pivot is asked of two fillets of opposite concavity when the edge
  the fillet `OnDiff` ends on is an edge of the face the fillet `OnSame`
  runs on, or of a coplanar piece beside it.
- That piece may be across a split that passes the vertex by, the fillet
  `OnSame` on the piece beyond ("Two fillets of opposite concavity where a
  split ends" took a split ending at the vertex): the corner's edge on the
  wall crosses the split and is cut there, and the split is cut on the
  side the fillet runs along.
- The fillet `OnSame` ending in two surfaces, its line crossing the split
  a little before the vertex: where the lines do not meet on its last
  surface and do on the one before, the corner is made of that one.

The corner is a filling (`GeomFill_ConstrainedFilling`) whose shape
follows the parameters of the face it lies against: 5e-3 of volume from
the refined shape's at radius 1, as far as the refined shape's own
mirror-image corners are from one another. One of the hexagon's sixteen
is not put to BOP's check: the top corner's side edge and inner edge at
0.3, a three-sided patch with a point for its fourth side, is called
self-intersecting there and is not at the bottom corner, its mirror image
-- the same outline to the last digit, no fold in either.

Not only on split walls: every such pair whose first fillet is walked was
a plate, and is the filling now (the sweeps, below).

| Case | What it covers |
|------|----------------|
| `issue962_hex_mouth_{top,bottom}_{mouth,side}_and_inner_r1` | the hexagon's: valid, the refined shape's volume to 1e-2, tolerance 1e-4, BOP's check (invalid before) |
| `issue962_hex_mouth_{top,bottom}_{mouth,side}_and_inner_r0.3` | the same at 0.3, the mouth's edge along the split: to 1e-3 (invalid, or a plate of tolerance 0.011) |
| `pocket_by_split{,_mirror}_corner_{mouth,side}_and_inner_r{0.3,1}` | the rectangle's: the refined shape's volume to 1e-4 (the mouth's edge with the inner edge refused; the side's a plate of tolerance 0.01 and 0.035) |

The picture case: `issue962_hex_mouth_top_mouth_and_inner_r1`.

## A plate's edge across an edge that passes the vertex by (realthunder/FreeCAD#962, 2026-10-12)

The last two of the 12: all three edges of the mouth's corner at radius
1. On the refined shape the corner is a sphere (`PerformThreeCorner`): the
two convex fillets have one base face. In pieces they have two, and the
corner is a plate (`PerformMoreThreeCorner`), whose edge on the wall runs
from the one fillet's line to the other's across the split. The plate is
made for that -- an edge over several faces, a piece on each, the edge
between two faces cut where the plate's edge crosses it. Which part of
that edge goes was told by its ends: the part from the end nearer the
vertex. That holds for an edge of the vertex. The split passes the vertex
by, 0.3 away, and runs 7.8 up and 10.4 down from it: the part the wall
keeps was dropped, the part under the fillet kept, both pieces left open.

Fix `d62136427b`: the part that goes is the one the vertex is beside, by the
vertex's projection on the edge. An edge of the vertex is cut as before.

Valid; a plate, not the sphere: tolerance 2e-3, 0.013 of volume from the
refined shape's on the hexagon, 0.03 on the rectangle. The same cut alone
made the plate of the mouth's edge and the inner edge at 1 valid, at
tolerance 0.12, before that corner became the filling above; and it lets
the corner setback fallback make the mouth's two edges at 1, refused
until the fix above, 0.21 of volume from the refined shape's.

| Case | What it covers |
|------|----------------|
| `issue962_hex_mouth_{top,bottom}_all_three_r1` | the hexagon's corner: valid, the refined shape's volume to 5e-2, no tolerance above 5e-3, BOP's check (invalid before) |
| `pocket_by_split{,_mirror}_corner_all_three_r1` | the rectangle's |

The picture case: `issue962_hex_mouth_top_all_three_r1`.

The sweeps, the four sections together. Edge: nothing changes.
Vertex: the 12 invalid results valid; 2 refused results made, the
mouth's two edges at radius 1; and 38 valid results moved -- pairs of
opposite concavity that were plates and are fillings: on #962 and the
miniatures from 0.02..0.06 of volume off the refined shape's at radius 1
to 5e-3 or less, their tolerances from 0.004..0.04 down to 1e-4; on shapes
with no split, #523's box, #631's and #273's, the same change of corner,
#631's largest tolerance from 0.18 to 1e-4. Nothing worse: 9204 valid,
209 invalid, 2829 refused.

Of the 86, 5 are left: 2 at #962's corner on a circle's edge, where one
of the two edges is 0.05 long and the radius 0.3 or 1; 2 at a vertex of
four sharp edges on #309, whose result on the refined shape passes
BRepCheck and fails BOP's check -- invalid there too, by the stricter
measure, like its edge 9 alone; and the fin's wall split, at radius 1
(Known broken).

Seen on the way, valid and not the refined shape's: the mouth's side edge
alone at radius 1 on #962 ends at the corner in the corner setback
fallback's plate, 0.025 of volume from the refined shape's, where the
fillet there is cut by the pocket's wall (the line crosses the split 0.23
before the vertex, and the fillet ends in two surfaces). Since: "An exact
fillet cut by its end face before a split", below.

## An exact fillet cut by its end face before a split (realthunder/FreeCAD#962, 2026-10-12)

The one seen on the way above: the hexagon's edge second from the split,
alone, at radius 1. Its fillet is a cylinder, and its line on the block's
side crosses the split 0.23 before the corner. `SplitKPart` cuts an exact
fillet where either line leaves its face and the rest of the edge is
walked, so the fillet ended in two surfaces, the last a sliver on the far
piece. But at that end the pocket's next wall cuts the fillet off 0.58
before the corner -- the hexagon's 120 degrees -- before the line reaches
the split at all. Of the sliver only a corner is left, and the curve the
fillet ends in crosses it, from one surface to the other.
`PerformOneCorner` makes that curve on one surface; the end failed
("bouchon non ecrit") and the corner setback fallback made it: valid, a
plate of tolerance 6e-4, 0.025 of volume from the refined shape's.

"The split within tolerance of the line's end" (above) already lets a
line run on over the far piece when the split is within tolerance of the
end. Fix `904a86b6c0`: it runs on as well at an end `OnSame` no other fillet
comes to, when the end face cuts it before the split -- the edge of the
line's face at the vertex that is not the spine's, carried on from the
vertex, meets the line in the part the face holds (`CutBeforeSplit`;
straight edges and lines). The fillet is one exact surface to its end and
the corner cuts it as on the side in one face. With another fillet at the
vertex the two surfaces stay: the corners of two and three fillets above
are made of them.

| Case | What it covers |
|------|----------------|
| `issue962_hex_mouth_{top,bottom}_side_r1` | the hexagon's second edge alone: the refined shape's volume to 1e-5, no tolerance above 2e-4, BOP's check (the fallback's plate before, 0.025 off) |

The picture case: `issue962_hex_mouth_top_side_r1`.

## Three fillets at a vertex where a split ends (2026-10-12)

The sweep fillets every edge of a vertex together, and at a vertex where a
split ends the split is one of them; the builder leaves it out, an edge
between two faces of one plane. Those results were set aside as having "an
edge that is a split itself, gone from the refined shape" -- 23 of them
invalid. Tried against the refined shape's other edges: 8 are #309's edge
9 again, invalid there too; the other 15 are the three sharp edges of the
vertex, valid on the refined shape -- the fin on its block, the slot with
its outer face in pieces, #962's corner of the edge 0.05 long.

Two of the three fillets run on the wall in two pieces, one on each.
`PerformThreeCorner` asks for a face in common of every two fillets;
these two have none, and the corner was a plate
(`PerformMoreThreeCorner`), inside out, its tolerances 0.07 to 2.6.

Fix `479cc80ecb`: where the corner would be a plate for that, the line of the
one fillet is shown on the other's piece while it is made (`PieceShown`),
as a fillet's line along a split is for the corners above. (Not otherwise:
three fillets that end in two surfaces each over the split -- the arm on
its block at 0.3 -- have their common faces already, and showing one of
them elsewhere took the exact corner they had away.) The corner is then
the one the wall in one face has -- a torus between the two convex
fillets around the concave one, or a filling -- built on that piece, and
its line on the wall runs from the one fillet's line to the other's, over
the split. That line is made to end on the split, and its piece from
there on is put on the other piece
(`StoreLineOverSplit`, which takes any curve now); the split is cut
there. Where the fillet shown turns out to be the corner's pivot, the
line is put back and the corner is the plate, as before.

| Case | What it covers |
|------|----------------|
| `fin_on_block_x{0,10}_all_three_r{0.3,1}` | the block's top edge, the fin's upright edge and the concave edge between fin and block: the refined shape's volume, no tolerance above 1e-3, BOP's check (invalid before, 0.08 and 0.41 of volume off) |
| `fin_on_block_wall_all_three_r{0.3,1}` | the same with the fin's wall split 0.7 from the side, the upright edge's fillet walked at 1 |
| `slot_split_outer_all_three_r{0.3,1}` | the slot's floor edge, its wall's edge and the floor's edge on the outer face in pieces (invalid before) |
| `arm_on_block_z{-9.75,-3.75}_all_three_r{0.3,1}` | the upright edge between arm and block with their two top (bottom) edges, at 137 degrees (a plate before, of tolerance 2e-3 and 5e-3 of volume off at 1) |

The picture case: `fin_on_block_x10_all_three_r1`.

## Two fillets on two pieces of a wall, ending apart on their edge (realthunder/FreeCAD#962, 2026-10-12)

The two at #962's corner on a circle's edge. An edge 0.05 long and the
upright edge below it, on the two pieces of a wall whose split ends at
their vertex -- "Two fillets on the two pieces of a wall" (above), but
for one condition of it: both fillets were to end at one point of the
edge behind. Here the one runs on a plane and the other on a cylinder,
and they end 0.005 apart on the circle between the two. A plate, inside
out, 1.1 and 16 of volume too much.

Fix `97f346ff4a`: the condition is dropped. `PerformTwoCornerbyInter` makes the
corner of two fillets that end at two points of their common edge as it
makes the other, cutting the larger by the face at the end between the
two; the line over the split is the same.

| Case | What it covers |
|------|----------------|
| `issue962_short_edge_and_upright_r{0.3,1}` | the 0.05 edge and the upright edge: the refined shape's volume to 1e-4, BOP's check (invalid before) |

The sweeps, these three sections together. Edge: #962's hexagon edge
second from the split and its mirror image at 0.8, the fallback's plate
before, are exact (0.013 of volume); nothing else changes. Vertex: 17
invalid results valid -- 15 the three fillets where a split ends, 2 the
fillets ending apart; 6 refused results made, the short edge's corner by
its other pairs; and 23 valid results moved: 10 the exact fillet to its
end (0.025 nearer the refined shape's), 8 plates of three fillets on the
arm and its block now that corner, at the refined shape's volume, 5 by
the fillets ending apart. Nothing worse: 9227 valid, 192 invalid, 2823
refused.

Of the 86 results once invalid only in pieces, 3 are left: 2 at a vertex
of four sharp edges on #309, invalid on the refined shape too by BOP's
check; and the fin's wall split, its two convex edges at radius 1 (Known
broken) -- with the concave edge as well it is made.
Of the 23 set aside for a split among their edges, 8 are left, #309's
edge 9 in each.

## The refused results, sorted by the refined shape (2026-10-12)

The sweeps' refused results had never been tried against the shape
refined, as the invalid ones were (`sweep/triage.py`). The edge sweep's
1370: 1045 are refused on the refined shape as well, 261 are on an edge
that is a split itself, 14 would be invalid there, and 50 -- 26 edges, on
#962's two inputs and four miniatures -- are refused only for the body
being in pieces. The vertex sweep's 2823: 2248 refused there too, 248 on
splits alone, 90 invalid there, and 237 refused only in pieces. The three
sections below make 36 of the 50 and 143 of the 237.

## A corner's cut over an end face in two pieces (realthunder/FreeCAD#962, #309, 2026-10-12)

Most of the 50 are one situation. The face the fillet ends on is kept in
two coplanar pieces, and the piece at the corner is narrower than the
fillet: one side of the fillet ends on an edge of the far piece, past the
vertex where the split between the two starts (its foot). The corner's cut
-- the curve the fillet ends in -- has to run over both pieces.

`PerformOneCorner` had that cut already, for an end `OnSame` on a wall in
two tangent faces ("The cut over a drafted wall's cone and plane", #876):
two curves meeting on the line of the edge between the faces, carried on
past its end, and a new edge along that line. It did not come to it here.
At an end `OnSame` one side of the fillet ends on an edge and the other
runs on in its face; that other side's line, on a face that goes on past
the vertex, ends on the face's far edge, wherever that is. With neither
end on an edge of the vertex the corner turned to that far edge for its
face at end before it looked for the wall in two, found no edge of the
vertex to extend, and failed. The slotted block's floor against the outer
face, the fin's block against the same, #962's four slots (edges 77 and 87
on the Fillet's input): refused from the width of the piece on.

At a corner of three edges alike -- all convex, all concave -- both sides
end on edges and the corner wants them on one face (`FindFace`). The strip
box past its strip's width (Known broken until now) is that: the line on
the bottom's far piece ends on the far end piece's edge, the other side on
the near end piece's.

Fix `74c8a201e0`, in `PerformOneCorner`:

- the wall in two faces is looked for before the other side's edge is
  tried for the face at end;
- an end that is not `OnSame`, one side on an edge of the vertex and the
  other on an edge of the piece beyond: the same cut in two curves, which
  here crosses the split itself rather than its line carried on. The split
  is cut at the crossing, and the edge of the near piece from the split's
  foot to the vertex goes under the fillet;
- the crossing within 1e-5 of the split's foot, at an end `OnSame` (a
  radius up to a thousandth or so over the piece's width): the new edge
  along the split's line would be that short -- 7e-7 at 0.701 on the slot,
  which BOP's check takes for no edge at all. The split starts at the
  crossing point instead, which takes the foot's place;
- the two curves end at the crossing point. `ChFi3d_ComputeCurves` takes a
  line's own end for the one asked when the two are within half a percent
  of the chord, so a piece could run on past the point by that much (the
  strip box at 2.005: "valid", tolerances of 0.0075, refused by BOP's
  check); each piece is cut at the point, and of two pieces on one plane
  each is the whole cut's curve, cut there, where that fits better.

| Case | What it covers |
|------|----------------|
| `strip_box{,_mirror}_r{2.0002,2.001,2.005,2.5,3.9}` | the strip box past its strip's width: the cross-section over the edge's 10, no tolerance above 1e-4, BOP's check (refused; XFAIL at 2.5 before) |
| `slot_split_wall_mouth_r{0.5,0.7,0.7001,0.701,0.705,0.8,2}` | the slotted block's floor against the outer face, the slot's wall split 0.7 from it: the cross-section over the edge's 3, BOP's check (refused from 0.7001 on) |
| `fin_on_block_wall_top_r{0.7001,0.8,2}` | the block's top against its side, ending under the fin's wall split 0.7 from the side (refused) |
| `blind_pocket_split_wall{,_mirror}_r{0.5,0.7,0.7001,0.701,0.705,0.8,2}` | a blind pocket's floor against its wall, the next wall split 0.7 from the corner, all three edges concave. Made before as well, by the loop over the faces at an end of several (`PerformIntersectionAtEnd`), which takes an arc past a split's foot; the corner's own cut now, to the same result |

The picture cases: `strip_box_r2.5`, `slot_split_wall_mouth_r0.8`.

## An edge that reaches the vertex through the end face's pieces (2026-10-12)

The slotted block with its outer face split as well, by the spine's own
line below the floor. Both sides of the fillet stop on edges at the
spine's end now: the outer face's on the split, an edge of the vertex,
and the floor's on the edge of the wall's far piece. `StartSol` took the
second for an obstacle -- an edge the fillet has to run along, the floor
against the wall -- and the walk along it failed.

"The fin on a split wall" (above) had the same question for the face the
fillet is on: an edge that reaches the vertex through that face's pieces
is where the fillet ends (`ChFi3d_EdgeOnSplitToVertex`). Fix `247fc423f1`: it
is asked the other way round as well, for the face the edge bounds on its
far side -- the wall, here -- by `StartSol` and by `PerformOneCorner`,
which chose the outer face's split for its face at end otherwise.

| Case | What it covers |
|------|----------------|
| `slot_split_both_mouth_r{0.7001,0.8,2}` | the slot's floor against the outer face, wall and outer face both split: the cross-section over the edge's 3, BOP's check (refused) |

The picture case: `slot_split_both_mouth_r0.8`.

## A line stopped on a split that ends at the vertex (realthunder/FreeCAD#962, 2026-10-12)

The tops of #962's outer ribs end at x=38.5 on a slope, and the block's
side below them is split at x=38.5 exactly: the piece of the side the
top's edge is on ends with the edge. The fillet's line on that piece stops
on the split, an edge of the corner's vertex; the other side ends on the
slope's edge with the top. Two edges that share no face.

"A fillet's line over a wall kept in coplanar pieces" (above) carries a
line that stopped in its face on over the split to the face at end, and
finds the crossing even where the split is within tolerance of the line's
end -- but was asked only for a side that is not on an edge. Fix `faf4f72ee0`:
a side on an edge of the vertex that is a split between its face and a
coplanar piece is taken as that.

On #962 the fillet is a chain from the arm's 45 degree underside up the
rib's front to its top (edge 72, or 94 and 171 on the other rib), and the
end went from the loop over the faces at an end to a plate
(`PerformMoreThreeCorner`), which failed: refused at every radius.

| Case | What it covers |
|------|----------------|
| `issue962_e{72,94}_r{0.3,0.8,2}` | the chain of either outer rib: the refined shape's volume to 1e-4, no tolerance above 2e-4, BOP's check (refused) |
| `slant_split_at_slope{,_mirror}_r{0.3,0.8,2}`, `..._chamfer_0.8` | the slant block split where its slope starts, one fillet on one edge: made before, by the loop over the faces at the end; the same volumes by the line carried over |

The picture case: `issue962_e72_r0.8`.

The sweeps, these three sections together. Edge: 36 refused results made
-- #962's slots (edges 77, 87 and the Chamfer input's 69, 79 at 0.8 and
2), its outer ribs' chains (72, 94, 171; 64, 86, 152 on the Chamfer
input, every radius), the arc at its arm's far end at 2 (17; 23), and the
miniatures' floor and top edges at 0.8 and 2; 16 valid results moved, one
chain of #962 at 2 (edges 57 to 97; 54 to 89 on the Chamfer input) whose
end at a slot's wall was the corner setback fallback's plate, tolerances
to 0.02 and 0.48 of volume off, now the refined shape's volume at 1e-4;
two more by 7e-6. Nothing lost: 2555 valid, 32 invalid, 1334 refused.
Vertex: 143 refused results made, each at the refined shape's volume --
the same edges alone at their ends and with the other edges there, on
#962 and the miniatures; 12 valid results on one miniature moved by 1e-5;
and one refused result invalid, below. Nothing lost: 9370 valid, 193
invalid, 2679 refused.

The one that turned invalid: the slotted block split twice, the floor's
edge on the outer face together with the floor's short edge on the wall's
piece at the mouth, at radius 1 (`mini_slot_bothsplit` V13:15,18). The
walk for the first failed before (the section above); it passes now, and
the corner of the two fillets, of opposite concavity, the one on the far
piece of the wall, comes out a patch with tolerances of 0.18 and the outer
face's wire crossed. The same pair on the block with its outer face whole
is refused at the vertex, as before; the refined shape makes it. Open.

Of the 50 edge results refused only in pieces, 14 are left: #962's edges
52 and 54 (49 and 51 on the Chamfer input) at 0.8 and 2, where the wall in
two pieces stands at a vertex of four sharp edges -- the loop over the
faces at such an end (`PerformIntersectionAtEnd`) has no cut over two
pieces; on the Fillet's input, edge 1, 0.05 long, at every radius and
edge 14 at 2; on the Chamfer's, edges 6 and 21 at 2. Of the 237 vertex
results, 93: 76 on #962's two inputs, 36 of them at those vertices of four
sharp edges, and 17 on the miniatures, pairs of edges.

## The cut over two pieces at a vertex of four edges (realthunder/FreeCAD#962, 2026-10-12)

The floors of #962's inner slots against the block's side (edges 52 and
54). At either end of the floor's edge stands a rib's wall, in two pieces,
the one at the floor's corner 0.4606 wide (0.6973 on edge 54) -- the
situation of "A corner's cut over an end face in two pieces" (above), but
the vertex has four sharp edges: the spine; the block's side going on under
the rib's 45 degree underside, in line with the spine; the underside's edge
with the wall; and the wall's with the floor.

With the wall in one face `PerformIntersectionAtEnd` has that end: one side
of the fillet on an edge of the vertex (the wall's with the floor), the
other running on in a face that goes on past the vertex
(`IntersectMoreCorner` -- the wall extended to the fillet, as at an end
`OnSame` of three edges, and an edge from the vertex along the wall's plane
to the fillet's line, between the cap and the block's side). In two pieces,
from the piece's width on, the floor's side ends on the far piece's edge:
neither side on an edge of the vertex, and the loop over the faces at the
end, starting from an edge that is not there, found none (`Failed to find
edge`). Refused.

Fix `3ba0c94072`: the end is recognised -- neither side on an edge of the
vertex, one of them on an edge that carries an edge of the vertex on past
the foot of a split of the wall (`ArcPastSplit`, asked for the wall) -- and
made by `PerformOneCorner`, which has the cut over two faces. One thing
differs at four edges: the edge from the vertex to the fillet's line carries
on, in the face that runs on, that face's other edge at the vertex (the
block's side under the underside), not the edge it carries on in the wall.

A miniature (the slot beside a slope, `slot_by_slope`) showed two more
things in the cut over two faces, both there since `74c8a201e0` (fixes
`bc752200fe` and `5635c27fba`):

- a face that carries a location (a prism moved into place, fused): the
  cut took the face's surface from its adaptor, which holds it without the
  location, and found the split's line off the surface (`the wall's tangent
  edge does not carry on`). Every case until now had its faces in place --
  or was refused by that alone: #474's bar at a radius just over its side's
  width (edges 21 and 26 at 2). Its walk leaves the side, too narrow, for
  the face beyond where there is one, and makes the last seventh of the
  edge; the corner there, a cut over the end face and a ramp tangent to it,
  failed on a face's location, and with that put right the fillet of a
  seventh came out, invalid. `PerformSetOfSurf` has the test for a surface
  that stops short of its spine's end -- by ten widths and half its edge;
  it takes three widths and three quarters of the edge as well (`4e97a46b0d`);
- where the cut crosses the split's line within 1e-5 of its foot the split
  starts at the crossing point, and its end stayed at the foot: the two
  faces' wires were open there by that distance, a vertex of tolerance 1e-5
  over it. Valid, and nothing for BOP's check, but on #962, 39 from the
  origin, 3e-5 of volume off. A straight split is now carried on to the
  point itself: tolerance 1e-7 there, the refined shape's volume to the
  last digit.

| Case | What it covers |
|------|----------------|
| `issue962_e52_r{0.4625,0.4635,0.465,0.8,2}`, `issue962_e54_r{0.8,2}` | the slots' floors on #962: the refined shape's volume to 1e-5, no tolerance above 2e-4, BOP's check (refused from the piece's width on) |
| `slot_by_slope{,_mirror,_both}_r{0.7001,0.701,0.705,0.8,2,3}` | the slot beside a slope, one wall or both split 0.7 from the block's side: the cross-section over the edge's 3 to 1e-5, BOP's check (refused) |
| `slot_by_slope{,_mirror,_both}_r{0.5,0.7}`, `slot_by_slope_one_r*` | the same narrower than the piece, and with the walls in one face: made before, coverage of the end at four edges |
| `issue474_f001_e{21,26}_r2` | #474's bar at a radius over its side's width: refused, or a valid solid (invalid for a moment, with the cut on a located face put right and a surface over a seventh of its edge let through) |

The picture cases: `slot_by_slope_r0.8`, `issue962_e52_r0.8`.

The sweeps. Edge: 8 refused results made -- #962's edges 52 and 54, and
49 and 51 on the Chamfer's input, at 0.8 and 2 -- each at the refined
shape's volume, tolerance 1e-4. Nothing else moved: 2563 valid, 32
invalid, 1326 refused. Vertex: the same edges alone at either end, at
radius 1, 8 made; and 12 refused results invalid. None of the 12 is this
corner's making: each is edge 52 or 54 (49, 51) filleted with other edges
at one of its ends, and was refused for the edge's other end alone. Eight
are the edge with the wall's short edge at the floor (`V36:52,80` and the
like) -- two fillets of opposite concavity at a vertex of four edges, a
plate; the same pairs are invalid at 0.3 already, and on the refined
shape at 1. Four are all four edges at the floor's corner
(`V36:51,52,74,80`, `V38:53,54,84,90`; `V34`, `V36` on the Chamfer's
input): valid at 0.3, made on the refined shape at 1, and in pieces the
corner's plate and the wall's two pieces come out invalid, tolerances to
0.008. Open. 9378 valid, 205 invalid, 2659 refused.

Of the 50 edge results refused only in pieces, 6 are left: on the
Fillet's input, edge 1, 0.05 long, at every radius and edge 14 at 2; on
the Chamfer's, edges 6 and 21 at 2. Of the 237 vertex results, 85: 81
refused -- 64 on #962's two inputs, 24 of them at the vertices of four
sharp edges above (pairs that leave edge 52 or 54 out, and all four edges
at its other end), and 17 on the miniatures -- and the four made invalid.

## A meeting kept on a surface that was removed (realthunder/FreeCAD#962, 2026-10-12)

All four edges at a slot floor's corner on #962, at radius 1: the four
results the section above left invalid, and the two it left refused at the
floors' other corners. The slot beside a slope has the same corner in
miniature, (0,4,5).

`PerformMoreThreeCorner` first finds where each fillet at the vertex meets
the next (`ChFi3d_SearchFD`): on which of the stripe's surfaces, and at what
parameter of its line there. A stripe that meets a neighbour farther along
than its last surface has the surfaces between removed -- they are under
the corner. The fillet of the floor's edge along the wall is a chain of two
edges here, the wall's piece at the corner 0.4606 long (0.6973; 0.7 on the
miniature), a surface for each. It meets the slope's fillet on the first,
0.41 from the vertex; and it meets the fillet of the slot's edge on the
block's side on the second, a radius from the vertex, past the piece. The
first surface is removed for that. The meeting with the slope's fillet
stayed as it was found -- the stripe's end surface, parameter 0.41 -- and
from then on meant the second surface's line, which starts where the piece
ends: a point the piece's length further along the wall. The plate took its
corners from the two stripes' ends, that far apart, with no edge between
them, and the wall's two pieces were left open: an open shell, 16 of the
miniature's volume missing. Upstream does the same.

Fix `726d9533c6`: when surfaces are removed from a stripe, its meeting with
the neighbour before is looked at again -- the point it was at, against
the stripe's new end surface at the same parameter. Where the two differ
the stripes no longer meet, and the corner's edge between them is one more
of the plate's, as between any two fillets that do not meet; here it
crosses the split ("A plate's edge across an edge that passes the vertex
by", above). The faces such an edge crosses were listed where surfaces
were removed -- by every removal at the vertex, whichever stripes it was
between: four faces here, from two removals, for an edge over two. Two
faces that share an edge are now the whole way.

| Case | What it covers |
|------|----------------|
| `slot_by_slope_all_four_r{0.8,1,1.5}` | the miniature's corner, its four edges: a valid solid within 0.1 (0.1 x r past 1) of the volume the refined shape's plate gives, no tolerance above 0.01, BOP's check (invalid, an open shell) |
| `slot_by_slope_all_four_r0.3` | the same narrower than the piece: made before |
| `issue962_floor_corner_y{13.7,17.1,20.3,23.7}_all_four_r1` | #962's four floor corners: the same (invalid at 13.7 and 20.3, refused at 17.1 and 23.7) |

The picture case: `slot_by_slope_all_four_r1`.

The sweeps. Edge: nothing moved. Vertex: the four invalid results valid,
and four refused ones made (`V37:52,53,81,82`, `V39:54,55,91,92`; `V35`,
`V37` on the Chamfer's input) -- tolerances of 0.006 and 0.007, within 0.07
of the refined shape's volume. Nothing else moved: 9386 valid, 201
invalid, 2655 refused.

Of the 237 vertex results refused only in pieces, 77 are left refused --
60 on #962's two inputs, 20 of them pairs at the floors' corners that
leave the slot's edge on the block's side out, and 17 on the miniatures --
and one invalid, `mini_slot_bothsplit` V13:15,18. The miniature's corner
has those pairs too: the floor's edge with the block's side's under the
slope from 0.8 on, and at 1 the slope's with either and the three
together, refused where the refined shape makes them.

## A set back corner on a fillet whose first edge is short (realthunder/FreeCAD#962, 2026-10-12)

Two of the four edges at the same corner, apart round the vertex: the
floor's along the wall and the block's side's under the slope
(`V36:51,80` on #962). The corner of two such fillets fails on the wall
in one face as well -- the curve between them is held to an edge's pcurve
past the edge's end -- and is made set back, each fillet cut a radius
from the vertex and the opening closed by one patch (the corner setback
fallback). In pieces that was refused too, twice over.

The setback is a distance from the vertex along the fillet's edge: for a
contact point, how far along the edge its nearest point is. The edge was
the one at the vertex. The floor's fillet is a chain, its first edge the
wall's piece at the corner; past that edge's end every contact point is as
far as the edge is long, 0.7, and a setback of a radius was never reached
-- on the stripe's first surface, which was dropped for it, nor on the
next: `a corner's setback runs past the stripe`. Fix `543ba5a661`: the
distance is taken along the spine, over its edges from the one at the
vertex on.

Made so, the result was thrown away. The fallback keeps a computation
whose fillets are all in the result (`AreFilletsMade`): the midpoint of
each edge filleted has to lie off the result's faces by half of what a
fillet moves it. The chain's short edge lies whole under the corner's
patch, which passes nearer to it than a fillet would -- at every setback
tried a valid result, and none kept. Fix `f446ee4591`: an edge of a spine
of several that lies whole within the setback of its end of the spine, or
the radius there, is not looked at.

| Case | What it covers |
|------|----------------|
| `slot_by_slope_floor_inline_r1`, `slot_by_slope_floor_inline_slope_r1` | the miniature's two edges, and those with the slope's: a valid solid within 0.15 of the volume the refined shape's corner has, no tolerance above 0.03, BOP's check (refused) |
| `slot_by_slope_floor_inline_r0.8` | the same at 0.8, without BOP's check: see below |
| `issue962_floor_corner_y{13.7,17.1}_floor_inline_r1` | the pair at two of #962's floor corners (refused) |

The picture case: `slot_by_slope_floor_inline_r1`.

The sweeps. Edge: nothing moved. Vertex: 25 refused results made, every
one refused only in pieces -- on #962, the pair above at the four floor
corners and the pairs at the slots' mouths (`V56:76,77` and the like), on
both inputs; on the miniatures, pairs on the slotted blocks and the fin's
wall. Within 0.11 of the refined shape's volume, tolerances to 0.005.
Nothing else moved: 9411 valid, 201 invalid, 2630 refused.

Open: the miniature's pair at radii other than 1. From 0.75 to 0.9 and at
1.2 the patch's edge on the wall is in two, a short piece of it past the
split, and the patch comes out loose -- 0.014 on all its edges at 0.8,
where the refined shape's has 4e-4 --: valid, and for BOP's check a
self-intersection (at 0.75, two edges too small). And at the corner still
refused only in pieces: the slope's edge with the block's side's (the
setback, on the floor's short edge here sharp, `exceeds an edge`) and
with the floor's (`Failed to find edge`), at radius 1. Of the 237 vertex
results, 52 are left refused and one invalid.

## A set back corner on a wall in pieces (realthunder/FreeCAD#962, 2026-10-13)

What the last section left open at the slot's corner, and the next
miniature's pair. Five faults, each of them where a corner made of
several fillets, or one set back, meets a face kept in coplanar pieces.

The slope's edge with the floor's, `Failed to find edge`. The corner reads
its edges and faces round the vertex, starting from the first fillet's
face. The slope's fillet is wider than the wall's piece at the corner and
ends on the next one, a face the vertex is not on: given first, it had
nowhere to start; given second, the corner was made. Fix `5b0741a75e`: the
reading starts from a fillet whose face holds the vertex.

The slope's edge with the block's side's under it, `a corner's setback
exceeds an edge`. Their corner fails whole or in pieces and is made set
back. The first setback tried is where the fillets meet, 0.41 from the
vertex, short of the piece's 0.7; the result was thrown away as invalid.
The face beside the floor's edge -- sharp here -- was still the far
piece, put there for the slope's fillet when that ended on it; the fillet
is cut back onto the near piece now, and the curve from its cut to the
floor's edge was drawn as one over two faces, the wall's near piece left
open. Fix `5e364dd15b`: the face beside a sharp edge is the piece that holds
the edge. At the next setbacks, a radius and more, the floor's edge was
cut farther from the vertex than its piece is long. The edge beyond the
split's foot carries it on: the cut is made on that one, the piece goes
whole, and the curve to the next cut crosses the split -- between two
sharp edges as between a fillet and one.

The floor's edge with the block's side's, valid and loose (the last
section's open end). A curve over several faces is held tangent to its
faces; one on a single face, from a fillet to a sharp edge, by its
position alone. Neither is right everywhere: the slot's patch, its other
curves held by position, came out 0.014 off its boundary at 0.8 for the
tangency of its wall's two pieces, and the fin's patch (`mini_finwall`
`V11:13,15`), its other curves tangent, is 9e-3 off without it and 6e-4
with. Fix `0892d3e167`: the patch of a set back corner with such a curve is
built both ways, and the one nearer its boundary is kept.

The slot's mouth on the block with both its wall and its outer face
split (`mini_slot_bothsplit` `V13:15,18`): the floor's edge along the
wall with the floor's on the outer face, `No intersection pc pc` at 0.3
and an invalid result at 1. The second fillet's line on the outer face
runs on past the vertex over the face's other piece, with nothing beside
it on the floor: its last surface has a face on one side only. The
corner of one fillet removes such a surface before it starts (upstream's
"the surplus is removed"); the corners of several, and the set back one,
took it for the fillet's end. Fix `e3c46a01d7`: they remove it too.

At 1 that pair's fillets no longer meet on the floor -- the one along the
wall is wider than the wall's piece -- and the corner is made set back.
The outer face's split below the vertex is in line with the wall's edge
above it, and two fillets beside two sharp edges in line are a case of
their own, its curves ending on the vertex; a set back corner, which never
reaches the vertex, took the case all the same and asked a single face
for a curve over the wall's two pieces (`a fillet ends off the face of
the curve to the next`). Fix `2ff60f1efd`: set back, the two edges in line
are cut like any other.

| Case | What it covers |
|------|----------------|
| `slot_by_slope{,_mirror}_slope_floor{,_reversed}_r1` | the slope's edge and the floor's, in either order and mirrored: the refined shape's volume within 0.01 (`Failed to find edge`; given floor first, made) |
| `slot_by_slope{,_mirror}_inline_slope{,_reversed}_r1` | the slope's edge and the block's side's: the refined shape's volume within 2e-3, no tolerance above 0.01 (refused) |
| `slot_by_slope_floor_inline_r{0.75,0.8,0.85,0.9,1,1.2}` | the floor's and the block's side's: within 0.06 of the refined shape's volume, no tolerance above 2e-3, BOP's check (0.014 to 0.028 loose and a self-intersection for BOP from 0.75 to 0.9 and at 1.2) |
| `slot_split_both_floor_and_end_r0.3` | the slot's mouth, wall and outer face both split: the refined shape's volume (refused) |
| `slot_split_both_floor_and_end_r1` | the same set back: within 0.15 of the refined shape's exact corner, no tolerance above 2e-3 (invalid, 6 of volume off) |

The picture cases: `slot_by_slope_inline_slope_r1`,
`slot_by_slope_slope_floor_r1`, `slot_split_both_floor_and_end_r1`; and
`slot_by_slope_floor_inline_r1` drawn again, its volume moved.

The carried edge is not reached by these: where the fillets meet is
short of the piece, and that first setback is valid now. It was measured
on a box with one wall split 0.7 from a corner, an edge of the corner
filleted at radius 1 and the corner set back by hand
(`BRepFilletAPI_MakeFillet::SetSetback`, which the suite has no way to):
at 0.5, 1.5 and 2 a valid solid within 0.03, 0.07 and 0.14 of the box in
one piece, refused before; at 3 the patch is not built and the corner is
still refused.

The sweeps. Edge: nothing moved. Vertex, at `2ff60f1efd`: 23 refused
results made and one invalid made valid, every one refused or invalid only
in pieces, and nothing lost -- 9435 valid, 200 invalid, 2607 refused. On
the two inputs of #962, at the four floor corners, the slope's edge with
each of its neighbours and with the spine's (`V36:51,74`, `V36:52,74`,
`V36:74,80` and the like, 18; tolerances 0.006 to 0.025, the slope's with
the floor's 0.105 as on the refined shape) and, at the rib's top corner,
the slanted edge with the top's (`V45:65,110`, 4, exact); and the
miniature's mouth pair at both radii.

45 valid results moved, none looser than the refined shape's. 24 are
corners of two fillets that had taken a surplus surface for a fillet's
end and were closed by a patch: the two fillets cut each other now, 1e-4
where the patch had 5e-4 to 0.02 and a face fewer in 16 -- on #631 (4,
0.16 of volume at radius 1), #962 (16) and `mini_armblock2` (4), whose
two mirrored corners differed by 0.005 and agree now. The 8 pairs of the
floor's edge with the block's side's at #962's floor corners are 0.02
nearer the refined shape's volume, 4.4e-4 like it; the 8 mouth pairs
there (`V56:76,77` and the like) and 5 of the miniatures' are tighter,
1.5e-3 to 5e-3 before and 6e-4 to 7e-4 now.

Open. The carried edge at three radii, above. The slope's edge with the
floor's is as loose as on the refined shape, 0.1. Of the 237
vertex results refused only in pieces 35 are left, and none invalid: most
are the next section's.

## Two fillets past their wall's piece, and the surfaces a corner removes (realthunder/FreeCAD#962, 2026-10-13)

Two more families of the vertex sweep's pairs refused only in pieces.

Two fillets at a vertex, both wider than the piece of the wall between
their edges: a box's corner with the wall in two faces, 0.7 of it at the
corner, each on a plane of its own (two bodies fused leave it so; with one
plane cut in two the corner is made as it stands), the two edges of that
piece filleted at radius 1. Each fillet ends on the piece
beyond the split, and the two face each other there, on a face the vertex
is not on. As a corner of two fillets that is refused (`fillets face to
face on a face off the vertex`, a wrong patch before that); set back, the
curve between the two cuts was asked of the piece at the vertex, `a fillet
ends off the face of the curve to the next`. Fix `2bc692bfc4`: set back, both
cuts are on the far piece and so is the curve -- the face between two
fillets is the one both end on. The corner is a patch where the refined
shape's is the exact one of two fillets on one face: 0.14 of volume apart
at radius 1.

The rib's top corner on #962, (38.5,10.2,32.25): the wall under the top's
edge is in two pieces, split by the edge that comes up to the vertex, 18
long. The fillet of the top's edge along that wall is a chain round the
wall's piece, six surfaces, and comes back to the long edge at its foot.
Before it makes a corner, `PerformMoreThreeCorner` removes from each
fillet the surfaces it will not use, the fillet run on past the vertex:
it keeps the last surface that has a point on an edge beside the fillet's
at the vertex -- looked for over all of them. The chain's first surface,
at its other end, has such a point; it was kept, the five others were
removed, and the corner went on to look for the edge between two faces
that share none (`Failed to find edge`). Upstream's fault, met here for
the long split. Fix `c4bb6a9cf4`: only the surfaces on the spine's edge at
the vertex, and past it, are looked at. (Narrower rules lost results: the
surface kept may start short of the spine's end, as #474's does at a
break point, and a sliver before it is rightly removed, as on #273.)

| Case | What it covers |
|------|----------------|
| `box_wall_two_faces_upright_and_bottom_r1` | the box's corner (the sweep's `mini_mini_wall`), the two edges of the wall's 0.7 piece: a valid solid within 0.2 of the refined shape's volume, no tolerance above 2e-3, BOP's check (refused) |
| `slot_split_{wall,both}_top_and_upright_r1` | the slotted block's wall, its piece's top edge and its upright one (refused) |
| `fin_on_block_wall_piece_{top,foot}_and_upright_r1` | the fin's wall, its piece's top edge and the edge at its foot, each with its upright one; the second without BOP's check, see Open (refused) |
| `issue962_mouth_y{17.1,20.3}_floor_and_upright_r1` | #962's slots' mouths: the floor's edge along the rib with the rib's upright edge (refused) |
| `issue962_rib_top_corner_r{0.3,1}` | the top's two edges at the rib's corner: within 1e-4 of the refined shape's volume, no tolerance above 1e-4 (refused; a patch 0.043 too large at 1 until `2ec760a1d3` made it the refined shape's exact corner) |

The picture cases: `slot_split_wall_top_and_upright_r1`,
`issue962_rib_top_corner_r1`.

The sweeps. Edge, at `2bc692bfc4`: 4 refused results made -- #273's
`Fillet001`, edges 3 and 9 at 0.3 and 0.8, the surface kept there too at
the wrong end of a chain; that input has no pieces, and the results are
the refined shape's. Vertex: 28 refused results made, nothing else moved
-- 9435 valid, 200 invalid, 2579 refused. The rib's top corners on #962's
two inputs (`V45:110,114`, `V72:173,177` and the chamfer's, 8;
tolerances 4e-4 and 1.2e-3) and five results of #273's `Fillet001` by the
second fix; by the first, the mouths' pairs on #962 (`V56:76,102` and the
like, 8) and the miniatures' (7), 4e-4 to 6e-4.

Open. Of the 237 vertex results refused only in pieces 12 are left, all
on #962: its edge 0.05 long, alone and with a neighbour (`Fillet` `V1`,
`V2`, 6), and the chamfer's edge 6 at radius 1, longer than the edge (6).
The fin's wall pair `V11:15,26` is made valid and fails BOP's check: an
edge of its patch lies 3% farther from the patch than its tolerance says
(`BOPAlgo_InvalidCurveOnSurface`); the pair at the piece's top,
`V16:23,26`, passes it.

## A fillet wider than its wall's piece at a pocket's mouth (realthunder/FreeCAD#962, 2026-10-13)

The edge sweep's last results refused only in pieces, six of them, all at
the round pocket's two mouths on #962: the pocket's wall is a cylinder,
the slot's a radial plane kept in two pieces, 1.25 of it beside the
pocket, and the block's top is split along a circle from the same foot.
Below, the pocket widens by that 1.25 under a step -- on the fillet's
input a cone and a ring 0.05 wide -- and only the wall's far piece goes
on down. Four faults, the last of them upstream's and on the refined
shape too.

The pocket's edge with the wall, wider than the wall's piece. At the
top the fillet ends on the far piece's edge with the top, past the foot
of the split, and the top there is in two pieces as well. The cut over
two pieces of the face at end (PerformOneCorner) takes a straight edge
between them, whose line it crosses; the circle goes to the loop over
the faces at end (PerformIntersectionAtEnd). That loop finds its faces
along the outline of the fillet's face, from the vertex to the edge the
fillet ends on. The fillet's face was the far piece, which the vertex
is not on: the way led down the split, to a face that shares no edge
with the last (`Failed to find edge`, `Failed to find element`). Fix
`9d58debece`: the outline is the wall's, over its pieces, and the faces at
end are those across it, as on the wall in one face; an edge between two
of them is kept on the side of a vertex on any of the wall's pieces.

At the foot the wall in one face carries the fillet's line on down
past the edge's end to where the wall ends, 3 or 4 below, and the fillet
with it: a fillet of a plane and a cylinder is made whole, each side as
far as its face goes, and cut by the step, the wider pocket and the
floor. In pieces the line is off the piece the edge is on; that fillet
was given up and walked instead, from the far piece -- and a walk stops
half the edge's length past its end, in the middle of the piece, where a
patch was tried (invalid, or refused). The second attempt, with the
spine carried on 1.5 radius, reaches the floor on the chamfer's input
and not on the fillet's. Fix `baf699efbb`: the fillet of the two surfaces is
made on the piece its line lies on. For one edge alone, neither end
OnSame, and only when it holds the whole of the edge's fillet: the
corners of an end OnSame and of a chain start from the walk's. (The
order of the two matters: the outline without the fillet on the far
piece lets the top through and leaves the patch at the foot, invalid.)

The step's edge with the wall, 1.25 long, and the 0.05 edge of the ring
(`OneCorner : bouchon non ecrit`). An end OnSame: the fillet's line on
the wall's piece ends on the split, and the split lies on the face at
end, the wider pocket's wall, which goes on up it. The line's crossing
with that face is its very end -- found 1e-15 past it, and taken for
none. Fix `6163e90334`: a crossing the last digits past the line's end is
its end.

The mirror edge, at the pocket's other mouth, came out invalid then --
and does on the refined shape, at any commit: 3387 of volume for 11584.
The fillet's cut crosses the edges between the faces at end; on a closed
curve the crossing comes on the curve's first turn, whatever the edge's
range, and an arc of the wider pocket's circle that runs from 3.95 to
9.10 was cut at 2.81 for 9.10: the faces beside it lost the edge whole.
Upstream's fault. Fix `7c3d8b9685`: the point is brought into the edge's
range.

| Case | What it covers |
|------|----------------|
| `pocket_mouth_plain_upright_r{1.5,2,2.5}` | a pocket and slot in miniature, no step: the pocket's edge, the wall and the top both split from one foot -- the refined shape's volume, no tolerance above 1e-5, BOP's check (refused) |
| `pocket_mouth_upright_r{1.5,2,2.5}` | the same with the step: the fillet runs on down the far piece to the floor (refused) |
| `pocket_mouth_wall_upright_r2` | the same, the top in one piece (refused) |
| `pocket_mouth_turned_step_r1` | the step's edge on the block turned 108.4 deg about z: within 0.01 of the refined shape's volume (refused; made on the block as it stands, the crossing found short of the end there) |
| `issue962_pocket_edge_r2` | #962's fillet input, edge 14 (refused) |
| `issue962_chamfer_base_pocket_edge_r2`, `issue962_chamfer_base_step_edge_r2` | the chamfer's input, edges 21 and 6 (refused) |
| `issue962_pocket_edge_mirror_r2`, `issue962_chamfer_base_pocket_edge_mirror_r2` | the same edges at the pocket's other mouth, edges 5 and 22 (refused) |
| `issue962_refined_pocket_edge_mirror_r2` | edge 5 on the fillet's input refined: 11582.3197 within 2e-3 (invalid, volume 3386.73 -- upstream's) |
| `issue474_f001_e12_r1` | #474's ramp edge, a shape with no pieces: no tolerance above 2e-4, BOP's check (0.025, the check failing) |

The picture cases: `pocket_mouth_upright_r2`, `issue962_pocket_edge_r2`.

The sweeps. Edge, at `9d58debece`: 8 refused results made -- the six
that were left refused only in pieces (`Fillet` E1 at 0.3, 0.8 and 2 and
E14 at 2, `Chamfer` E6 and E21 at 2) and the two mirror edges, refused in
pieces and invalid on the refined shape (`Fillet` E5, `Chamfer` E22 at
2); all eight the refined shape's volume within 1.3e-3, tolerances 2e-7.
Three valid results moved: `Chamfer` E6 at 0.3 and 0.8, made set back
before (0.008 and 0.16 off the refined shape's, tolerances 3e-3 and
9e-3), are the refined shape's at 2e-7, and the sweep's box with a wall in
two faces, edge 1 at 2, is exact (991.4159265). 2575 valid, 32 invalid,
1314 refused. Vertex: 12 refused results made -- the twelve that were
left: `Fillet` V1 and V2 with the 0.05 edge, `Chamfer` V2 and V6 with
edge 6 at 1. 38 valid results moved: 30 of #474's `Fillet001`, the
ramp's edges 12, 28, 37 and 45 at 1, alone and with a neighbour -- valid
with a tolerance of 0.025 and failing BOP's check, 1e-4 and clean now,
0.012 less of volume (the crossing at the line's end, on a shape with no
pieces: the suite's `issue474_f001_e12_r1`); six of `Chamfer` V2 and V6
with edge 6 at 0.3, as the edge alone; two of the box, 7e-6. One refused
result is invalid now: `Fillet` V1:1,6 at 0.3, the 0.05 edge with the
cone's edge beside it. Edge 6 alone is invalid there, in pieces and
refined (upstream's, `sweep/README.md`); the pair was refused for edge 1,
and is still refused on the refined shape. 9475 valid, 201 invalid, 2566
refused.

Open. Of the results refused only in pieces none is left on either
sweep (the lists of `sweep/README.md`: 50 edge results, 237 vertex
results). The pair `Fillet` V1:1,6 at 0.3, above, invalid for its edge
6. The volumes of the step's edge differ from the refined shape's by up
to 0.01 (radius 2.5 on the miniature), both valid at 1.5e-7: the cut's
curve on the wider pocket's wall is an approximation either way, and the
two shapes do not get the same one.

## The far piece's fillet at an end OnSame (2026-10-13)

The fin's last invalid result: its upright edge with the block's top edge
at the L's inner corner, the fin's wall split 0.7 from the side as well,
at radius 1 (`fin_on_block_wall_top_and_upright_r1`, XFAIL since "Two
fillets on the two pieces of a wall"). The upright edge's fillet is wider
than the wall's piece, its line on the wall on the piece beyond. It was
walked, from the far piece -- a B-spline, where the wall in one face has a
cylinder. The corner of two fillets on the two pieces of the side cuts
them by one another, and takes a cylinder or a plane for the one that
stops on the split, a surface that goes on past its end as it is; this
one was left to the plate, which came out inside out: 767.2220 for
766.4705, a tolerance of 0.19.

The fillet of the piece its line lies on (`baf699efbb`, "A fillet wider
than its wall's piece at a pocket's mouth") was kept from an end OnSame --
the foot here, where the side runs on down past the fin. That was settled
while the rule was still wide: tried at such ends it broke corners that
carry the walk's line over the split (`StoreLineOverSplit`). The rule as
it ended -- one edge, the whole of its fillet in one surface -- gives the
same suite and the same sweeps with the exception and without it, but for
this fin. Fix `5052552dd6`: the exception is gone. The upright edge's
fillet is the cylinder, and the corner the refined shape's.

| Case | What it covers |
|------|----------------|
| `fin_on_block_wall_top_and_upright_r1` | the refined shape's volume to 1e-6, no tolerance above 1e-5, BOP's check (XFAIL before: invalid) |

The picture case: `fin_on_block_wall_top_and_upright_r1`.

The sweeps. Edge: `mini_finwall` E26, the upright edge alone, is the
exact 762.2743339 at 2 (the walk's 762.2743322) and moves in the tenth
digit at 0.8; 2575 valid, 32 invalid, 1314 refused as before. Vertex:
V11:13,26 at 1 -- this corner -- invalid before, valid; seven valid results
with the upright edge at 1 moved, by 5e-5 at most (the walk's fillet
before, the cylinder now), and the four edges of V11 among them are down
from a tolerance of 8.6e-6 to 1e-6. 9476 valid, 200 invalid, 2566
refused. Nothing else moved.

Open. The same fin's other two pairs at radius 1 with the wall's 0.7
piece of the concave edge -- with the top edge (V11:13,15) and with the
upright edge (V11:15,26) -- are valid and not the refined shape's: 770.6492
for 770.7360 and 770.2217 for 770.3068, at tolerances of 3e-3 and 3.6e-4
(the second fails BOP's check by a hair, "Two fillets past their wall's
piece"). The concave edge's fillet is in two surfaces there, one for each
piece of the wall, and the two fillets' lines meet 1 from the vertex, on
the second: the corner of two fillets is made of their end surfaces
(`TwoCorner : No intersection pc pc`, `fillets face to face on a face off
the vertex`), and Compute runs again with the corner set back, a plate.
(Made since, the two surfaces one: "A fillet in two surfaces at a corner
of two".)

## A side stopped on a split in the plane of the face at end (realthunder/FreeCAD#962, 2026-10-13)

Found by a new comparison: the sweeps' results that are valid in pieces,
each made again on the refined shape, with BOP's check on both
(`sweep/README.md`, "Valid in pieces, and the same?"). Six edges of #962
came out loose where the refined shape's fillet is exact.

The arm meets the block at (38.5,10.2) and (38.5,27.2). The block goes on
above the arm, and its sides y=10.2 and y=27.2 are split at the arm's top,
z=-3.75: each split is an edge of the vertex there, and lies in the plane
of the arm's top. Three edges end at those vertices with a side on the
block's side -- the upright edge between arm and block at y=10.2, concave
(edge 49; 46 on the chamfer's input), and the block's own two edges above
the arm (50 and 56; 47 and 53). The line on the block's side stops on the
split.

On the side in one face the vertex has four edges; one side of the fillet
ends on an edge of the vertex and the other runs on past it in its face.
`IntersectMoreCorner` cuts the fillet by the one face at end, beside the
first side -- the arm's top -- and extends that face over the fillet's end
to the section. In pieces both sides end on edges of the vertex, five of
them, and the loop over the faces at end (`PerformIntersectionAtEnd`)
took the three faces round the vertex in turn: the arm's top, the block's
wall above it, the side's other piece. The fillet stops short of the edge
between the first two, and the end was left to a plate
(`PerformMoreThreeCorner`): valid, with tolerances of 3e-3 to 7e-2, the
volume off by up to 0.31 at radius 2, and BOP's check failing on the
upright edge at 0.8 and 1. Edges 50 and 56 at 0.8 are the plates of "A
corner plate folded to stay tangent" above, held to 0.05 since.

Fix `6505747185`: a side that ends on a split of its own face, an edge of
the vertex lying in the plane of the face at end beside the other side,
has that face alone cut. The fillet's end is its section in that plane,
from the other side's edge to the split; the face grows over it up to the
split from the vertex to the line's end, which it shares with the side's
piece beyond from then on -- the loop's case of one intersection, with
the split itself for the edge that is kept. The faces between are left
as they are.

Not where a wall stands on that face in the way of the section
(`SectionCrossesEndFace`, "A fillet's end under a wall that runs on past
the corner"): the arm's other upright edge, at y=27.2 (edge 36; 33),
convex, whose end runs under the block's wall. That end is a plate on the
side in one face as well; the rule taken there made it invalid.

| Case | What it covers |
|------|----------------|
| `arm_on_tall_block_near_split_down_r{0.3,0.8,2}` | the arm on the taller block, the block's side y=10.2 split at the arm's top: the upright edge between them -- the refined shape's volume to 1e-5, no tolerance above 2e-4, BOP's check (a plate: tolerances 3.6e-3 to 6.7e-2, BOP's check failing at 0.8 and 2) |
| `arm_on_tall_block_near_split_up_r{0.3,0.8,2}` | the block's edge above the arm there (a plate: 3.5e-3 to 2.3e-2, the volume 0.14 short at 2) |
| `arm_on_tall_block_far_split_up_r{0.3,0.8,2}` | the block's edge above the arm at y=27.2, that side split (a plate: 5.2e-3 to 3.4e-2, 0.31 short at 2) |
| `issue962_arm_upright_r0.8`, `issue962_block_edge_over_arm_r2`, `issue962_block_far_edge_over_arm_r2` | the model's own, edges 49, 50 and 56 |
| `issue962_e50_r{0.3,0.8}`, `issue962_e56_r0.8` | held to the quarter round's volume, 2e-4 and BOP's check now (they were held to 0.05) |

The picture cases: `arm_on_tall_block_near_split_down_r2`,
`issue962_block_far_edge_over_arm_r2`.

Open. The arm's upright edge at y=27.2 (#962's edge 36; 33): a plate,
with tolerances of 0.02 to 0.06, and BOP's check fails -- in pieces and
on the refined shape alike. Its fillet's end lies under the block's wall:
the cut needs a face of its own there, in the plane of the arm's top and
facing down.

## An arch on a plate: a point on a face without its edge, and pieces taken for tangent faces (realthunder/FreeCAD#309, 2026-10-13)

#309's arch stands on a plate as long as its diameter: the cylinder comes
down to the plate's top where the plate ends, tangent to the end. The edge
at the arch's foot, between its end face and the plate's top, 100 long,
was invalid at every radius in pieces -- and on the refined shape valid by
BRepCheck with a vertex at a tolerance of 100 and an edge at 69, BOP's
check failing. It was counted with upstream's (`sweep/README.md`) until
the comparison of the section above showed the refined result's surfaces
to be the right ones.

At each end three faces meet the fillet round the vertex: the arch's end
face, the fillet's own; the cylinder; and the plate's end, tangent to the
cylinder along the edge between them. The cut is the cylinder's. The
fillet's side on the end face stops on the arch's circle, a little short
of the vertex (0.04 at radius 2); the other stops on the top's edge with
the plate's end, an edge in line with the tangent one: two edges in line,
one face of intersection (`PerformIntersectionAtEnd`). The cylinder grows
over the fillet's end down to the top's edge, which lies on it and is
none of its face's edges.

Two faults.

The parameters of the end's two points on the face that is cut are read
from the pcurves of their edges on it. For an edge that has none the
surface is extended and the point projected on it -- a B-spline or a
Bezier; on any other surface the parameters were left as they stood,
(0,0) on the first face. On #309 the cut came out right all the same and
the point took the distance for its tolerance; on the miniature the cut
is wrong: valid, 671 of volume for 797 at radius 0.8, a vertex at a
tolerance of 21. Upstream's fault, on a body in one piece. Fix
`9c45825ba1`: the point is projected on the surface as it is, and brought
into the face's range on a periodic one.

In pieces the plate's end is two faces, split under the arch's end face,
and the vertex has five edges. Two tangent faces in a row and a third
are a case of their own there (pro15368): the two are passed over as one
and the third is cut. The cylinder, tangent to the end's first piece, and
that piece, "tangent" to the second across the split, passed for it, and
the fillet was cut by the end's plane -- 0.04 off the point on the arch's
circle: an end section at a tolerance of 0.042, and the cylinder's wire
left open. Fix `358d611f3f`: the pieces of one face are no tangent faces
there. The vertex is one of four edges, two of them in line, the face
between them in pieces ("A corner of five edges, two of them in line"),
and the cylinder is cut.

| Case | What it covers |
|------|----------------|
| `arch_on_plate_foot_r{0.3,0.8,2}` | a half cylinder of radius 10 on a plate 20 long, in one piece: the edge at its foot -- the volume taken, no tolerance above 1e-5, BOP's check (valid at 747, 671 and 809 for 795, 797 and 811, tolerances of 15 to 21: upstream's) |
| `arch_on_plate_split_foot_r{0.3,0.8,2}` | the same with the plate's ends split under the arch's end face: the refined shape's volume to 1e-5 (invalid) |
| `issue309_refined_arch_foot_r{0.3,0.8,2}` | the model's edge 9 on the refined shape: no tolerance above 2e-4, BOP's check (a vertex at 100) |
| `issue309_arch_foot_r{0.3,0.8,2}` | in pieces: the refined shape's volume to 1e-3 (invalid) |

The picture cases: `arch_on_plate_foot_r0.8`,
`arch_on_plate_split_foot_r0.8`.

The sweeps, this section and the one above. Edge: #309's E9
invalid at the three radii, valid; 18 valid results moved to the refined
shape's -- #962's six edges, tolerances of 3e-3 to 7e-2 down to 1e-4; and
the plate's top edges at its ends on #309 (E23, E24, at 0.3 and 0.8) the
same volume with a face less. 2578 valid, 29 invalid, 1314 refused.
Vertex: 24 invalid results valid, every case with #309's edge 9 at its
two ends; 84 valid results with #962's six edges moved to the exact
volume at 1e-4; 28 of #309 a face less. 9500 valid, 176 invalid, 2566
refused. Nothing lost on either.

## A fillet's last surface past the vertex, on its face's next piece (realthunder/FreeCAD#474, 2026-10-13)

The comparison's one edge left: #474's Fillet002 input, edge 13, an
upright edge of the block under the ramp, between the block's end wall
and its side. The wall is in two pieces, split at the level where the
ramp starts. The ramp rises from there along the side, and the side's
top edge with it: the fillet's line on the side runs on 0.027 past the
split's level (radius 0.3) before it meets the ramp's edge. A fillet of
two planes is cut where a line leaves its face -- two surfaces, the second
from the split's level to the ramp's edge, on the wall's upper piece. On
the wall in one face they are one.

When a fillet has more surfaces than edges, the loop over the faces at
end (`PerformIntersectionAtEnd`) asks whether an edge beside the spine is
a tangent one. If the surface before the last ends on such an edge on
both sides, the last one is dropped; if on one, the end is a plate
(`PerformMoreThreeCorner`). The split passed for the tangent edge, the
surface before the last ends on it on the wall's side alone, and the end
was a plate: a tolerance of 0.05 for the refined shape's 1.6e-5, BOP's
check failing, 0.035 of volume off at radius 0.8.

Fix `afb7f305d0`. Where the last surface lies on the next coplanar piece
of one of the fillet's faces, past a split that is an edge of the vertex,
and its other side ends on an edge of the vertex, the surface before it
takes that side's end over and the last one goes: one surface, whose side
on the wall stops on the split -- what the corner would cut off the line
on the upper piece anyway. And the rule of "A side stopped on a split in
the plane of the face at end" takes a split that lies on the surface of
the face at end, a plane or not: the ramp is a B-spline surface, the
split its straight end. The ramp alone is cut, as on the wall in one face.

| Case | What it covers |
|------|----------------|
| `issue474_f002_wall_edge_r{0.3,0.8}` | #474's Fillet002 input, edge 13: the refined shape's volume to 1e-4, no tolerance above 2e-4, BOP's check (a plate: tolerance 0.05, BOP's check failing) |

The picture case: `issue474_f002_wall_edge_r0.8`.

The sweeps. Edge: the edge's two results moved to the refined shape's,
tolerance 0.05 down to 1e-4; 2578 valid, 29 invalid, 1314 refused.
Vertex: 12 valid results with it, at its two ends, the same way (0.05 and
0.065 at radius 1); 9500 valid, 176 invalid, 2566 refused. Nothing else
moved.

## A line carried over a split to the pivot of two fillets (2026-10-13)

The same comparison on the vertex sweep: the arm fused to a block as
tall, their tops (and bottoms) one plane in two faces, split along
x=38.5. At (38.5,27.2) the block's top edge along y=27.2 with the upright
edge between arm and block -- a plate, with tolerances of 3.6e-3 at radius
0.3 and 1.2e-2 at 1 for the refined shape's 5e-6 and 1.7e-5, the volume
0.074 off at 1 (`mini_armblock2` V7:9,11 and V8:10,11, `mini_ab_r3`
V9:12,20 and V10:14,20).

Two fillets at a vertex are cut by one another
(`PerformTwoCornerbyInter`) when their lines on the sides away from the
face they share end on one edge, the pivot: here the arm's top edge with
its side, which the upright edge's fillet ends on, and which the top
edge's line on the top reaches 0.77 past the block (radius 0.3). In
pieces that line stops on the split between the block's top and the
arm's, short of the pivot: "fillets are not on the same arc", and the
corner went to the plate.

Fix `2ec760a1d3`: the line that stops on a split of its face, when the
other fillet's edge is an edge of the piece beyond the split and of the
other fillet's face, is carried over the split to that edge for the cut
-- its face the piece beyond, its end on the pivot, as it runs on the face
in one piece. Then it ends on the split again; its piece from there to
the pivot is put on the piece beyond and on its own fillet
(`StoreLineOverSplit`, as "Two fillets on the two pieces of a wall" does
on the shared side), and the pivot is cut where the line ends on it. A
straight line on a cylinder or a plane, which goes on past its end as it
is.

| Case | What it covers |
|------|----------------|
| `arm_on_block_far_z{-9.75,-3.75}_upright_and_block_r{0.3,1}` | the pair at the arm's top and at its bottom: the refined shape's volume to 1e-5, no tolerance above 2e-4, BOP's check (a plate: 3.6e-3 and 1.2e-2, 0.074 of volume off at 1) |

The picture case: `arm_on_block_far_z-3.75_upright_and_block_r1`.

The sweeps. Edge: nothing moved. Vertex: 20 valid results
moved, none lost. The miniatures' 8 -- the pair at either end of the
upright edge, at 0.3 and 1 -- to the refined shape's volume at 1e-4. On
#962 the rib's top corner at y=10.2, its two top edges (`Chamfer`
V41:99,103 and V65:154,158, `Fillet` V45:110,114 and V72:173,177), the
same way, from 3.7e-4 and 1.2e-3; and the arm's top edge with its upright
edge at y=27.2 (`Chamfer` V11:33,34, `Fillet` V16:36,37), whose other
corner is still the plate of the upright edge alone: the volume within
1e-3 of the refined shape's, 0.07 off at radius 1 before. 9500 valid, 176
invalid, 2566 refused.

The rib top corners of #962 (`Chamfer` V74:103,114 and V89:127,163, the
`Fillet` input's V83 and V102) were plates the same way, 3.7e-3 for
1.3e-5 at radius 0.3: there the pivot itself is in two pieces in line, a
split's foot between them. The next section.

## The pivot of two fillets in two pieces (realthunder/FreeCAD#962, 2026-10-13)

The rib's top corners on #962, the last pairs the comparison with the
refined shape left loose: at (38.5,13.7,32.25) the top's edge with the
rib's slope and its edge with the wall beside it, y=13.7 -- a plate,
3.7e-3 of tolerance at radius 0.3 for the refined shape's 1.3e-5, the
volume 0.003 off, and 0.1 off at radius 1 (`Chamfer` V74:103,114 and
V89:127,163, the `Fillet` input's twins).

The wall is in two pieces, split 0.46 from the corner, and the split's
foot is on the slope's edge with the wall. That edge is the pivot, the
edge both fillets end on, and it is in two pieces itself: the first 0.52
long, dropping 0.24 on the way. The slope's fillet ends on the first
piece, 0.07 from the vertex. The wall's fillet has its line on the wall
0.3 below the top or more -- under the first piece's end: on the wall in
one face it runs on 0.57 past the corner to the slope's edge, and the two
fillets are cut by one another there (`PerformTwoCornerbyInter`). In
pieces the line ended where the fillet's edge does, in the middle of the
wall's first piece, on no edge at all: no pivot, and the corner went to
the plate.

Fix `52a5c89410`, in two parts. The line carried over a split to the pivot
(`2ec760a1d3`) was one that stops on the split; a line that ends in its
face short of the split, straight on, is carried the same way, the split
the first one of its face it crosses. And the pivot it is carried to may
be the second piece of the edge the other fillet ends on: an edge of the
piece of the wall beyond the split and of the other fillet's face, which
goes on, tangent, from the first piece's other end, the split's foot
(`ChFi3d_PivotInTwoPieces`). `PerformTwoCornerbyInter` then has the two
fillets' points on two edges, where it sent every such corner to the
plate ("fillets are not on the same arc"): the two pieces are one pivot,
the piece at the vertex, with the far point at its parameter on that
piece's curve, past its end. The cut itself needs no more -- the wider
fillet is cut by the other's face to its own point on the edge, an edge
of that face whichever piece it is.

| Case | What it covers |
|------|----------------|
| `issue962_rib_top_{near,far}_r{0.3,0.8,1}` | the pair at the rib's two top corners beside the split walls, y=13.7 and y=17.1: the refined shape's volume to 1e-4, no tolerance above 2e-4, BOP's check (a plate: 3.7e-3, the volume 0.003 off at 0.3 and 0.1 at 1) |

The picture case: `issue962_rib_top_near_r1`.

## An edge's tolerance over its curves on the faces (realthunder/FreeCAD#962, 2026-10-13)

The pairs the comparison left valid on both shapes with BOP's check
failing only in pieces, five of them, all on #962.

One is a tolerance. The pocket's mouth, the wall's edge with the circle
of the cone below it, radius 1 (`Fillet` V8:10,14): "invalid curve on
surface". The two fillets are cut by one another along a curve whose ends
are put on the points known on each of them, and the curve is farthest
off the wall's fillet a little inside its end: 2.51e-6 at 0.003 of it for
2.18e-6 at the end. The builder's last pass (`BRepLib::SameParameter`)
gives an edge the largest distance at its samples and a twentieth more,
2.29e-6 here; BOP's check looks for the largest distance. On the refined
shape the same margin held by chance, 7.32e-6 for 7.63e-6 -- upstream's
fault, and no matter of pieces. Fix `b72e581675`: after that pass an edge
the fillet made takes the largest distance of its curves on the faces of
the result when that is more than its tolerance, looked for as BOP's
check does (`BRepLib_CheckCurveOnSurface`), its vertices with it. Only
for a curve or a curve on a surface that is not a line or a conic, and
never an edge of the input. That search on every edge cost the suite 9%
and the vertex sweep a quarter of its time; the distance is taken at ten
times the samples first and followed to its peak, and only an edge that
comes out within a fiftieth of its tolerance, or over it, is searched.
That costs nothing that shows (90.3 s for 90.3).

Two are one plate. The rib's chain at its bottom end, (38.5,17.1,14),
radius 1 (`Chamfer` V35:73,74, `Fillet` V37:81,82): a plate with a
tolerance of 0.1 on the refined shape as well, where BOP's check happens
to pass. Not a matter of pieces; the plate is the fault.

Two are one patch. The hex pocket's mouth, the mouth's edge with the
pocket's upright edge, of opposite concavity (`Fillet` V48:67,120 at 0.3,
V51:70,126 at 1): "self-intersecting face", the three-sided patch
between the two fillets. It is made by the same code from the same three
boundaries on both shapes (`GeomFill_ConstrainedFilling`); what differs
is the block's top, a plane with other axes once refined, and with it the
patch's degrees -- 8 by 5 in 16 by 18 poles for 6 by 8 in 7 by 16 -- while
its edges, its area to 2e-4 and its angles to the faces beside it (0 on
the plane, up to 8 deg on a fillet, on both) are the same. Left as it is.

| Case | What it covers |
|------|----------------|
| `issue962_pocket_wall_and_cone_r1` | the pocket's pair: BOP's check, no tolerance above 1e-4, the refined shape's volume to 2e-3 ("invalid curve on surface") |

The sweeps. Edge: nothing moved. Vertex: 12 valid results
moved, none lost, all on #962 and all from a plate to the refined
shape's volume at a tolerance of 1e-4: the rib's top corners at y=13.7
and y=17.1 at radius 0.3 and 1 (`Chamfer` V74:103,114 and V89:127,163,
`Fillet` V83:114,132 and V102:146,183, from 3.7e-3 and 1.2e-2), and at
radius 1 the same corner at the rib's other walls (`Chamfer` V92:133,163
and V105:150,158, `Fillet` V105:152,183 and V118:169,177, from 1.8e-3).
9500 valid, 176 invalid, 2566 refused.

Open. The plate at the rib chain's bottom end, 0.1 of tolerance on
both shapes. (#962 `Fillet` E36 and `Chamfer` E33, the arm's edge that
ends under the block's wall, with a plate over the arm's top that was
loose and refused by BOP on both shapes, and the fin wall's two pairs
whose corner was set back where the refined shape's is not, are made
since: the next two sections.)

## A ceiling under a wall at a fillet's end (realthunder/FreeCAD#962, 2026-10-13)

The last single edge the comparison with the refined shape left loose: #962
`Fillet` E36 and `Chamfer` E33, the upright edge between the arm's side and
the block's side y=27.2, at its top end -- the corner (38.5,27.2,-3.75),
where the block's wall x=38.5 stands on the arm's top. The fix of
2026-10-03 ("A fillet's end under a wall that runs on past the corner")
made that end valid with the corner plate, on the block's side in one face
as in two. Valid was all it was: a tolerance of 0.006 to 0.06 on the
fillet and up to 0.19 on the chamfer, 0.007 of volume off at radius 2 for
0.052 taken (0.36 on the chamfer at 2), and BOP's check refusing the
fillet's -- on both shapes, so the comparison had nothing to say about it.

The plate covers the corner between the vertex and the section's two ends,
in the plane of the arm's top. On the arm's side of the wall's edge that is
the arm's top itself, which nothing cut: two faces back to back. And a
plate there cannot be tangent to the fillet, which stands upright on it.

What is there is plain. The fillet ends in the plane of the arm's top. Its
section in that plane runs from the edge of the arm's side to the block's
side, and on the way crosses the edge between the arm's top and the wall,
at a point X. Up to X the section cuts the arm's top. From X on it runs
under the wall: the fillet has taken what was below, the block is above,
and the body is closed by a face in the plane of the arm's top that faces
down -- a ceiling. Its three sides are the section from X on, the piece of
the wall's edge from the vertex to X, which the wall keeps where the arm's
top has lost it, and the way back from the section's end to the vertex on
the block's side: the split's piece from the vertex, which the face above
the split keeps, or, on the side in one face, a new edge on that face.

Fix `0669daa0b6` (`CeilingAtEnd`, called by `PerformIntersectionAtEnd` at a
vertex of more than three edges before it looks for the faces to cut).
One side of the fillet ends on an edge of the vertex; the face across
that edge, the face at end, is a plane; the other side's line crosses that
plane on its own face, which runs on past the vertex, or ends on a split of
that face in coplanar pieces; the face at end's other edge at the vertex
runs into the corner between the two (`SectionCrossesEndFace`, as before);
and there are no faces at the vertex but the fillet's two, the face at end,
the wall, and the piece above the split. The fillet's surface is cut by the
plane in one curve from side to side, and the curve is cut in two at X,
found in the plane where the curve crosses the wall's edge: once, and
inside both. The first piece goes on the face at end, as any corner's
curve; the second on a surface of the DS, the same plane the other way up,
with its curves the other way round. The wall's edge is cut at X and its
piece from the vertex is given again as a curve between the wall and the
ceiling, and so is the split's piece, between the face above and the
ceiling; on the side in one face the line is cut where it crosses the
plane (not at the section through the first side's end: the plane need
not be square to the edge) and the third side is a line on that face. The
vertex stays, and the edge filleted is ended at it: a face that keeps the
vertex -- the block's side in one face does -- kept the edge with it.
Anything else -- a face at end that is no plane, the other side's face no
plane where a new edge is wanted on it, more faces at the vertex, a
section that misses the wall's edge or meets it at an end -- is left to the
plate, as before.

| | before | now |
|--|--|--|
| arm on the block, side in two faces, r 0.1 / 0.3 / 0.8 / 2 | tolerance 0.0065 / 0.020 / 0.023 / 0.059, BOP refuses | 1e-7, BOP clean, the corner's section over the edge's 6 to 1e-6 |
| the same, side in one face | 0.0063 / 0.021 / 0.025 / 0.061, BOP refuses | the same |
| #962 `Fillet` E36, r 0.1 / 0.3 / 0.8 / 2 | 0.0065 / 0.019 / 0.021 / 0.061, BOP refuses; refined 0.0066 / 0.019 / 0.024 / 0.061 | 2.1e-7 on both, BOP clean, one volume to the last digit |
| #962 `Chamfer` E33, d 0.1 / 0.3 / 0.8 / 2 | 0.009 / 0.029 / 0.074 / 0.18; volume 0.36 short at 2 | 1e-4 (the chamfer's other end), one volume on both |

| Case | What it covers |
|------|----------------|
| `arm_on_tall_block_r{0.1,0.3,0.8,2}`, `arm_on_tall_block_whole_r{0.1,0.3,0.5,0.8,2}` | the corner, the block's side in two faces and in one: the closed form's volume to 1e-6, no tolerance above 1e-6, BOP's check (valid was all they asked before) |
| `arm_on_tall_block_chamfer_d{0.3,2}`, `arm_on_tall_block_whole_chamfer_d{0.3,2}` | the chamfer there: its section a line, the same ceiling |
| `arm_on_tall_block_mirror_{x,z,xz}_r{0.3,2}`, `arm_on_tall_block_whole_mirror_{x,z,xz}_r{0.3,2}` | mirror images: the fillet's other side on the edge of the vertex, its other end at the corner |
| `arm_tilted_under_block_{up_x,down_x,up_y,down_y,skew}_r{0.3,2}` | the arm's top tilted 4.6 deg each way and askew: the line crosses the plane above or below the corner, the section is an arc of an ellipse; the section's area times the plane's height over its centroid, to 1e-6 |
| `issue962_e36_r{0.1,0.3,0.8,2}`, `issue962_e36_chamfer_d{0.3,2}` | the model's own edge: the same three checks (0.8 and 2 are new; 0.1 and 0.3 asked for validity) |

The sweeps. Edge: six results moved and nothing else -- that edge on
the two shapes at 0.3, 0.8 and 2, from a tolerance of 0.019, 0.021 and
0.061 to 2.1e-7. Vertex: 28 valid results moved, every one with that edge
among its edges, at its two ends -- alone, in pairs and with all the
edges of the vertex: from 0.019 at 0.3 and 0.030 at 1 to 2.1e-7, or to
1e-4 where a second fillet brings its own. No status changed: 2578 valid,
29 invalid, 1314 refused; 9500, 176, 2566. Of the suite's 41 cases of this
section, new or tightened, every one fails on the build before.
## A fillet in two surfaces at a corner of two (realthunder/FreeCAD#962, 2026-10-13)

The fin wall's two pairs the comparison with the refined shape left as
set back plates (`mini_finwall` V11:13,15 and V11:15,26 at 1): the 0.7
piece of the concave edge under the fin's wall, with the block's top edge
and with the fin's upright edge. Valid, and 0.087 and 0.085 of volume off
the refined shape's corner.

The wall is in two coplanar pieces, split 0.7 from the outer face, and
the split's foot is on the concave edge: the edge is two edges, and its
fillet two surfaces, one for each. A corner of two fillets is made of
their surfaces at the vertex. At a radius above 0.7 the two lines on the
face the fillets share meet past the split's foot, on the surface before
the last: with the top edge's fillet on the block's top, 1 from the
vertex ("TwoCorner : No intersection pc pc"); with the upright edge's,
which is wider than the wall's piece at the vertex and lies on the far
piece, on that far piece ("fillets face to face on a face off the
vertex"). Both were refused, and Compute made the corner again set back,
with a plate.

On the wall in one face the fillet is one surface, and the corner is the
exact one of two fillets of opposite concavity: a patch between the one
fillet cut where the lines meet, the other cut across from there to its
end on an edge of the vertex, and the face beside.

Fix `9735ff8875` (`PerformTwoCorner`). Where the lines do not meet, or the
fillets share no face, and the fillet that ends on an edge of the vertex
(OnDiff) has two surfaces or more, its last two are made one, if they are
one: the same face on one side, coplanar pieces on the other with the
split between them where the line of the one before the last stops, both
lines straight, and that one's surface and curves, carried on as they
are, passing through the last one's two ends. The surface before the last
takes the last one's end on the common side and the last one goes. On the
pieces' side, twice. First the line is shown on the piece at the vertex,
to the last surface's end there: for fillets that meet on the face they
both lie on whole (the block's top); when the corner is made the line
ends on the split again and its piece beyond is put on the piece at the
vertex and on the fillet, as a line over a split wall
(`StoreLineOverSplit`), with the fillet's end and the cut of the edge it
ends on. Else it is left on its own piece: the other fillet lies on that
piece too, the lines meet on it short of the split, and the corner cuts
the line there. A meeting within 1e-3 of the split is not taken -- a
fillet as wide as the piece has its line along the split -- and whatever
fails later leaves the two surfaces as they were.

| pair, radius | before | now | refined |
|--|--|--|--|
| foot and top, 0.70001 / 0.71 / 0.8 | 770.3172 / 770.2787 / 770.5097, tolerance to 0.054 | 770.3472 / 770.3576 / 770.4593, 1e-4 | the same to 2e-6 |
| foot and top, 1 / 1.5 / 2 | 770.6492 / 770.9980 / 772.5666 | 770.7360 / 771.7596 / 773.3126 | the same to 2e-6 |
| foot and upright, 0.71 / 0.8 / 1 | 770.1107 / 770.1410 / 770.2217 | 770.1412 / 770.1846 / 770.3068 | to 6e-5 |
| foot and upright, 1.5 / 2 | 770.5069 / 770.9153 | 770.7940 / 771.5958 | to 6e-5 |
| the slot's floor edge and its end, 1 (`slot_split_both`) | 1131.4815 | 1131.5944 | the same |
| #962's mouths, floor and upright, y=17.1, 0.8 / 1 / 1.5 | 11582.3841 / 11581.4006 / refused | 11582.4199 / 11581.4810 / 11578.2358 | 11582.4196 / 11581.4709 / 11578.2359 |
| the same, y=20.3 | 11582.3841 / 11581.4006 / 11577.9994 | 11582.4251 / 11581.4804 / 11578.2701 | 11582.4196 / 11581.4709 / 11578.2359 |

The foot's pair with the upright edge keeps the 6e-5 it has at radius
0.3, where nothing is made one: the patch between the two fillets is a
filling, and differs with the parameters of the faces it lies between.
#962's mouths keep more, 0.034 at most, and by corner: the two at the
high-y walls of their slots (y=17.1 and 23.7) are the refined shape's to
1e-4 at radius 1.5 and one of them at 1, their mirror images (y=13.7 and
20.3) 0.009 off at 1 and 0.034 at 1.5 -- the patch's area 2.919 for 2.903
on y=20.3. The filling again, turning with the parameters of the faces
beside it. (This section said until `8558180119` that the upright edge's
fillet, walked there, was the cause. It was walked, and is the refined
shape's cylinder since; the corners moved by 1e-5 with that.) At radius
0.7 itself,
and up to 0.7001, the pair with the upright edge is as before (refused
at 0.7, a plate above).

| Case | What it covers |
|------|----------------|
| `fin_on_block_wall_piece_foot_and_top_r{0.70001,0.71,0.8,1,1.5,2}` | the 0.7 piece with the block's top edge: the refined shape's volume to 1e-5, no tolerance above 2e-4, BOP's check (new) |
| `fin_on_block_wall_piece_foot_and_upright_r{0.71,0.8,1,1.5,2}` | with the fin's upright edge: to 2e-4 (radius 1 asked for 0.2 and no BOP check before; the others are new) |
| `slot_split_both_floor_and_end_r1` | the slot's floor edge along the split wall with the floor's on the outer face: to 1e-4, tolerance 2e-4 (0.15 and 2e-3 before) |
| `issue962_mouth_y{17.1,20.3}_floor_and_upright_r{0.8,1,1.5}` | the model's own: to 0.05, tolerance 2e-4 (0.2 and 2e-3 at radius 1 before; 0.8 and 1.5 are new, y=17.1 at 1.5 was refused) |

The picture cases: `fin_on_block_wall_piece_foot_and_top_r1`,
`fin_on_block_wall_piece_foot_and_upright_r1`,
`issue962_mouth_y17.1_floor_and_upright_r1.5`.

The sweeps, run on the fix without its 1e-3 rule, which only takes
results back. Edge: nothing moved. Vertex: no status changed (9500 valid,
176 invalid, 2566 refused), and 24 valid results moved, every one a set
back plate at radius 1: the fin's two; six on the three slotted
miniatures, the 0.7 piece of the floor's edge with the wall's upright
edge and with the floor's edge on the outer face (V13:15,16 and
V13:15,18), the refined shape's volume to 1.4e-5 at a tolerance of 1e-4
for 4e-4 to 2e-3; and 16 on #962, eight on each input, at the four
slots' mouths -- the floor's piece with the rib's upright edge and with
the floor's edge on the outer face -- within 0.01 of the refined shape's
where the plates were 0.07 and 0.09 off, at 1e-4 for 5e-4 and 6e-4.

BOP's check. All 24 passed it as plates. Of the 14 looked at since --
the `Chamfer` input's eight and six of the `Fillet`'s; the run was
stopped there, and of the other ten the fin's two and three of the
miniatures' were looked at by hand and pass -- three fail it now: "self
intersecting face", the patch between the floor's piece and the floor's
edge on the outer face (`Chamfer` V57:78,79 and V58:79,80, `Fillet`
V64:86,87). The refined shape's result fails the same check at two of
the mirror corners (`Chamfer` V49:68,69, `Fillet` V56:76,77), where the
pieces pass. The patch is `GeomFill_ConstrainedFilling`'s on both, the
one of "An edge's tolerance over its curves on the faces" above, and
BOP's verdict on it turns with the parameters of the faces beside it.
Not chased; the suite's #962 mouths are the pair with the upright edge,
which passes.

(Run since, on the installed build at `594ece7109`, 2026-10-14: the two
sweeps on the fix's last state are this baseline to the line, FreeCAD's
`TestPartApp` 282 and `TestPartDesignApp` 368 less the one known, the
draft sweeps the same 1222, 500 and 114.)
## The far piece's fillet for an edge of a chain (realthunder/FreeCAD#962, 2026-10-14)

A fillet wider than the piece of a split wall its edge is on is made on
the piece its line lies on, exact, as on the wall in one face
(`baf699efbb`, `5052552dd6`) -- for a contour of one edge. #962's slots'
mouths have the rib's upright edge first of a chain of five, three on the
refined shape: the rib's top arc is in two pieces as the wall is. On the
wall's piece at the mouth, 0.69 wide, the first two were walked at radius
0.8 and up, B-splines where the refined shape has a cylinder and a torus.

Two things kept the rule from a chain. At an end OnSame `SplitKPart`
looks for the edge beside the spine in each of the fillet's faces, and
the far piece does not hold the end vertex: "Failed to find element",
taken for "the walk makes this one". And the far piece's surface for the
arc's first piece is the whole arc's torus, running over the next edge's
range, which that edge makes itself: taken, the torus was there twice
and the result invalid (11576.56 for 11578.87).

Fix `8558180119`. The edge beside the spine is looked for in the spine's
own piece, the face of the spine's edge that is coplanar with the far
one. And for an edge of a chain the far piece's surface is taken when it
is that edge's and no more: it may run on past the spine's own ends, not
over a neighbour's range. The arc's first piece is left to the second's
surface, which covers it, as before.

| Case | What it covers |
|------|----------------|
| `issue962_mouth_upright_r1_cylinder` | the rib's upright edge alone at radius 1: valid, a cylinder face more and no B-spline face (walked before) |
| `issue962_hex_mouth_edge_r0.8_cylinder` | the hex pocket's mouth edge at 0.8: the same |

The sweeps. No status changed in either. Edge: the miniatures' upright
edge at 2 moves in the tenth digit, the walk's value to the cylinder's
(1122.274334), and #962 `Fillet` E68 at 0.8, the hex pocket's mouth edge,
is a cylinder for a B-spline: its end ellipses carry the tolerance the
refined shape's do, 1.3e-5, where the walked ends had 2e-7 -- the one
"tolerance worse" the comparison prints. Vertex: E68 alone at its two
ends at 1 the same way; the slotted miniatures' floor and upright pair
(V13:15,16) at 1 is the refined shape's volume to the last digit,
1130.306793 for 1130.30678; #962's V56:76,102 moves by 2e-5. 2578 valid,
29 invalid, 1314 refused; 9500, 176, 2566.

Nothing to picture: the surface is the one that was there, exact.

## BOP's check on every valid result (realthunder/FreeCAD#474, #876, #273, #523, 2026-10-14)

The sweeps call a result valid on BRepCheck's word. The feature after a
fillet is a boolean, and a boolean asks BOP's argument check
(`Shape.check(True)`), which is stricter: the suite has put single cases
to it since #523's pinched top, the sweeps never had. `sweep/fsw_bop.py`
does (sweep/README.md): every valid result of a sweep, with what the
check reports.

At `8558180119`, on the inputs that pass the check themselves -- #273's
`Fillet001` and #876's `Fillet001` do not, and their results are set
aside -- 60 of the edge sweep's 2395 valid results fail it, and 423 of the
vertex sweep's 8849. #962's two inputs, #631's four, #309, #523 and the
nine miniatures have none on the edge sweep. 323 of the 423 report "too
small edge". Three faults, fixed here; what is left is mostly corner
plates at loose tolerances (below).

### An edge of no length

An edge the fillet made with nothing between its ends:

- #474's `Fillet003` has two faces of its hexagon with a needle: at
  (6.415,11.307) and at (4.441,7.828) two of a face's edges lie on one
  line for 2 of height, 1.4e-7 apart. A fillet ending at either corner
  crosses the needle with an edge of that length between two vertices.
- #876's post is flush with the plate's round end and drafted by a
  degree, so the edge at its foot is a degree from smooth. Its fillet is
  thousandths wide and ends in an edge 1.1e-6 long at radius 0.3, 1.0e-4
  long between ends 5.1e-5 apart at radius 2.
- #273's handle stands on the cylinder's wall two degrees from it; the
  fillet down a front edge of the handle ends at its foot in an edge
  1.5e-5 long, closed on one vertex.

BRepCheck lets such an edge be. BOP's check calls it too small and its
two vertices, or the edge and the faces beside it, self-intersecting.

Fix `61f59f6842`, `ChFi3d_DropMicroEdges` in `ChFi3d_Builder.cxx`, run on
the result before the pinched faces are split. An edge the fillet made
-- not one of the input's -- no longer than twice the tolerance the
fillet's surfaces are made to (2e-4 by default: its ends, each known to
1e-4, are one point), and that BOP's own test finds covered by its
vertices (`BOPTools_AlgoTools::IsMicroEdge`), is taken out of its wires
and its two vertices made one: the input's when one of them is, with the
tolerance to hold the other. An edge closed on one vertex just goes. The
builder's history is carried over as for the pinched faces. No member,
no exported symbol.

The length is the limit that matters. Without it the pass took an edge
0.029 long under vertices at a tolerance of 0.045, on #273's edge 5 at
0.3 -- a loose result, which stayed loose and whose volume moved by 1.9.
An edge its vertices cover and that is longer than the fillet's own
tolerance is the mark of a loose result, not an edge of no length.

What it costs: the wire is open by the edge's length where it was, under
the vertex. The volume moves by that length times its lever: 5.0e-4 at
most (#876's edge 53 at radius 2, 8665.7574 to 8665.7579), the adaptive
integration (1e-10) agreeing with the default one on both shapes.

| Case | What it covers |
|------|----------------|
| `issue474_f003_no_width_e{53,13,5}_r0.3` | the hexagon's bottom edge and the thread's two helices, each ending at a needle: valid, BOP's check ("too small edge" before) |
| `issue876_post_foot_e10_r0.3` | the edge at the post's foot, a degree from smooth: the same (edges 42 and 53 at 2 dropped from the suite: their corners come out loose with one compiler or another -- 42 with gcc, 0.02 and 0.24 of volume less; 53 with MSVC, 0.0115 and 0.19 less -- other paths, not the pass's) |
| `issue273_handle_foot_e{12,14}_r0.3` | the handle's front edges, ending at its foot two degrees from the wall: the same |

### A pinch between two new vertices

#523's box and cylinder, the bottom: the cylinder's rim and one of the
box's two edges it ends on, filleted at radius 1. The rim's fillet
touches the bottom on a whole circle of radius 1 and the edge's on a line
tangent to it, so the bottom is a rectangle and a disc meeting at a point
-- the pinched top of `40ba54dcdf` again, but the circle ran from one
vertex the fillet made to another at the same place, and the pass that
splits a pinched face took only a pinch at a vertex of the input's, and
none with an edge between its two vertices. BOP's check: the two vertices
self-intersecting.

Fix `1a971d66bc`, `FindPinch`. Two vertices the fillet made are a pinch
too, the looser kept; and an edge between them does not rule it out when
it is itself a loop of the wire -- longer than ten times what the
vertices cover. Such a loop keeps its range when its vertices are made
one (the parameter update the other edges get would have collapsed it).

| Case | What it covers |
|------|----------------|
| `issue523_bottom_rim_and_edge_{a,b,c,d}_r1` | the rim and either box edge, at both ends of the rim: valid, the bottom in two faces, BOP's check (two vertices at one point before) |

### The roots of a trigonometric equation below zero

#474's first input has a corner of three planes, two of them five
degrees off square, at (-13,1.992,-0.176). Fillet the two edges on the
third and the fillets are two cylinders meeting in an exact quarter of an
ellipse. BOP's check called the two cylinders self-intersecting: it took
their common edge for a new section. The edge's range on its ellipse is
-PI/2..0, and on that range BOP found no projection of a point lying on
it (`IntTools_Context::ComputePE`, `GeomAPI_ProjectPointOnCurve` -- the
same point projects on the range moved by a period).

The fault is upstream's and old, in `TKMath`:
`math_TrigonometricFunctionRoots` finds the roots in [0, 2 PI) and brings
them to the bounds asked by the whole periods in the lower bound, rounded
toward zero (`IntegerPart`, `std::trunc` since 8.0). For a lower bound
below zero that is no period at all: every root between the bound and
zero was out of range, and dropped. Its first- and second-degree branches
did not bring a root up a period for a positive bound either.

Fix `5c531f4938`: one function brings each root up or down by whole
periods to the first value not below the lower bound (less the branch's
tolerance), in all six places. Checked against the old code on 400000
random equations of every form the solver has a branch for, half with a
lower bound below zero (`../math/trig_roots.cpp`): the old missed 150272
roots a sampling finds by a change of sign, the new none; no root the old
found is lost, and every new one is a root within the bounds.

| Case | What it covers |
|------|----------------|
| `issue474_skew_corner_r{0.3,1}` | the corner's two edges: valid, no tolerance above 1e-5, BOP's check (two cylinders self-intersecting before) |

### The sweeps

No status lost on either sweep; no result whose BOP check was clean
reports anything now. Edge: 3 results invalid before are valid, #474's
`Fillet003` edge 56 at every radius, the other needle's hexagon edge; 19
valid results moved by up to 7e-4 in volume, every one an edge of no
length dropped. Vertex: 11 invalid before are valid, the same edge 56
alone and with its neighbours at V27 and V32; 123 valid results moved
the same way, and #523's four pairs have the bottom in two faces. 2581
valid, 26 invalid, 1314 refused; 9511, 165, 2566. `TKMath`'s fix moves
no fillet in either sweep: it changes what BOP finds, not what the
builder makes. It does move one draft: the new draft makes #876's face 44
at 5 degrees, refused before for want of a closure (valid, BOP's check
clean; the draft sweep's baseline has the line).

BOP's check (`baseline/bop_*.txt`): the edge sweep's 60 are 28 -- #474's
`Fillet003` 30 to 10, #876's `Fillet` 8 to none, #273's `Fillet` 20 to
16, #474's `Fillet002` 2 as they were. The vertex sweep's 423 are 213 --
`Fillet003` 208 to 74, #876 46 to 2, #273 83 to 59, #523 4 to none, the
skewed corner's 4 to none. The suite, the draft suite (99) and the
thickness suite (378) pass on the three.

What is left, and why:

- #474's `Fillet003`, the thread's upper helix (edges 3, 8, 16, 32 and 40
  and the pairs holding them): the fillet's end is a vertex on one of the
  needle's two edges, at a tolerance of 7e-6 that reaches the other,
  1.4e-7 away ("self-intersecting vertex"; the input's own vertices there
  are at 1e-7). The input's.
- Corner plates at loose tolerances -- 3e-3 to 0.37 -- on #631's four
  inputs, #962's two (V20 to V23 and V34 to V37, both inputs), #273 and
  #474's `Fillet002` (edge 4's plate at 0.008). The plate's quality,
  which fcad's `docs/CornerBlending.md` corner blend is for. Looked at
  on #631's V8, edges 9 and 21 at 0.3 (two fillets with no face in
  common at a vertex of four convex edges): the two fillets' ends meet
  the edge between their other faces 0.0025 apart (0.8% of the radius),
  and the plate has that piece of the edge for a side. The plate misses
  its boundary by 1.9e-4 but is 8.5 deg off tangent to the fillets, its
  approximation 1e-3 off the curves near that side, and the corner's
  tolerance is 0.0031 (1% of the radius at every radius): the side is
  "too small" under it. More points on the boundaries make the plate
  tangent (G1 0.148 rad at ten, 0.006 at thirty) and the result looser
  (0.014); a tighter approximation does nothing; dropping the side, as an
  edge of no length, satisfies the check and moves the volume by 0.24
  (the wires open by 0.0025 at a lever of ~100). Not taken.
- #876's V39, its edges 52 and 53 together: two edges each a degree from
  smooth, filleted at 0.3 -- the fillets a few thousandths wide, 0.005 of
  tolerance. Left.
- #273's results at tolerances of 0.04 to 0.26, on an input with two
  vertices at 0.03; and its edges 23 and 24 at 0.8, a corner's patch at
  the tip of a groove that the check calls self-intersecting.
- #962's three `GeomFill` patches at the slots' mouths (`Fillet` V48,
  V51, V64; `Chamfer` V57 and the like), at 1e-4: "self-intersecting
  face" -- the patch of "An edge's tolerance over its curves on the
  faces", whose verdict turns with the parameters of the faces beside
  it.

Nothing to picture for the first and the last: the edge is not to be
seen at any scale a picture has, and the fillets are the shapes they
were. #523's first pair is pictured (stage `s523e`).

Run since on the installed build -- the three on `256171494a`, the merge
of the fork's `raisedCounter` work, FreeCAD built again against it: the
suites plain and frozen (568 and the one known failure, 99, 378), both
sweeps and both BOP sweeps the baselines to the line, FreeCAD's
`TestPartApp` 282 and `TestPartDesignApp` 368 less the one known, the
draft sweeps the same but the one draft above, the gtests of Part and
Import, the ABI checks (no layout moved, no fork-only import).

## A boss flush with the plate's side (2026-10-14)

A cylinder boss (radius 5) on a plate (30 x 20 x 3), standing flush with
the plate's side: the cylinder touches the side's plane along its line
x = 15, and its foot circle touches the plate's top edge at (15,0,3). The
top narrows to nothing there. A fillet round the foot was refused at every
radius, "TopOpeBRepDS_DataStructure::Point" -- a point of index 0. The
same boss set 3 in from the side was made.

The foot is one closed contour, both its ends at the tangent vertex. Its
fillet runs round the boss, a torus, until its line on the plate meets
the plate's top edge -- at (18.317,0,3) and (11.683,0,3) for radius 1 --
and stops there. Its line on the boss stops at (17.764,0.833,4) and
(12.236,0.833,4), short of the side. The vertex then holds the one stripe
twice, two ends that have no corner made for them: nothing gave their
points an index, and the DS was asked for point 0.

What the result is to be: the side carried up as it is, flat. The fillet
made on a plate reaching past the side, then cut by the side's plane --
the ring loses what hangs over the edge, and the side grows a peak above
the plate's top, up to (15,0,4) for radius 1, under the fillet's two cut
ends. The boss's foot is then the fillet's line all round, closed at that
point.

Fix `b234546fbe`, `PerformPinchEnds` in `ChFi3d_Builder.cxx`, tried
first at a vertex holding one stripe twice. Each end's line on the boss
is run on past the end, on the fillet's surface, to where it touches the
side (the least distance to it, zero); the two ends must touch at one
point. Each end is cut by the side's surface from its point on the
plate's edge to that point: in steps across the fillet, a root along it
for each, interpolated, with its curves on the fillet's surface and the
side's. The line on the boss is moved to the point, and the two cuts go
in as the stripe's ends, with the side's surface untrimmed under them.
No member, no exported function (the weak typeinfo of
`NCollection_HArray1<gp_Pnt>` is exported now, as ten of upstream's
toolkits export it).

Where the boss touches the side, the fillet is tangent to both, so the
side's surface meets the fillet's in two branches crossing at the point:
each end's cut crosses its line there, and the cut is good to 1e-7. It is
made only so:

- the fillet's surface runs on exactly past its end -- a periodic one,
  the torus round a cylinder on a plane; a walked surface is not run on;
- the side's surface is elementary (a plane, a cylinder, ...);
- the fillet is tangent to the side at the point. A chamfer is not: its
  cut reaches its line on the boss tangent to it, a corner of no angle,
  and the result was invalid; refused, as before;
- the two cuts meet on the side's surface as in space: a closed side
  whose seam runs through the vertex (a round plate's rim, with its seam
  there) would need the seam carried up to the point; refused, as before.

The result is the fillet made on a wider plate and cut, to the boolean:
`boss_flush_csg_r{1,2}` makes both and finds nothing of either outside
the other. The volumes agree within 1e-4 (2591.84203 and 2591.84205 at
radius 1), the default integration over the cut's B-spline.

Not this, at first: a drafted boss (a cone narrowing upward) touches the
side only at the foot, and the fillet's line on it never reaches the side
-- made since, "A drafted boss flush with the plate's side", below. The
boss at a corner of the plate, flush with two sides, is refused before any
corner is made; so was the rim's boss turned with its own seam opposite the
tangent point (the walk fails; made since `892a10b753`, "A walk past a closed
spine's end", below).

| Case | What it covers |
|------|----------------|
| `boss_flush_foot_r{0.3,1,2,4.5}` | the foot at four radii, up to near the boss's own: valid, BOP's check, no tolerance above 1e-5 (refused before) |
| `boss_flush_turned_foot_r1` | the boss turned half a turn, its seam on the far side: the foot one edge, both ends on it |
| `boss_flush_two_feet_r1` | two flush bosses on one side, both feet |
| `boss_flush_foot_and_top_r1` | the foot and the boss's top edge together |
| `boss_rim_foot_r{0.3,1,2}` | a round plate (radius 20), the boss against its rim from inside: the side a cylinder |
| `boss_flush_csg_r{1,2}` | the result against the fillet on a wider plate, cut by the side |
| `boss_flush_chamfer_r1`, `boss_rim_seam_foot_r1`, `boss_corner_foot_r1` | still refused: XFAIL (Known broken) |

The sweeps (edge, vertex): no case moved; BOP's check over them as at
`5c531f4938` (28 and 213 reported), with the cases the baseline still
skips because `baseline/edge.txt` had them invalid before `61f59f6842`:
#474's `Fillet003` edge 56, 3 cases, and the vertex sweep's 11 (V27 and
V32 with edge 56) run now -- clean, but `V27:46,56@1` (0.053, a too small
edge). The draft sweep (the new draft makes fillets): valid 1222,
refused 500, chains 114, all the same. The suite (579, 5 XFAIL), the
draft suite (99) and the thickness suite (378) pass.

## A chamfer carried past a corner where its faces turn tangent (`a2f5c2a5d4`, 2026-10-15)

x16win's case: a 40x30x10 block, fillet 2 on its edges at y=30 (the two
verticals, the top one) and on (0,30,0)-(0,0,0), then chamfer 1 on the
top edge x=0. The fillet on the top back edge and the one on the left
back vertical meet in a mitre, an ellipse from (0,28,10) to (2,30,8) with
no corner patch, tangent to the chamfered edge at (0,28,10); the chamfer
runs on along it (its spine is the edge and the ellipse, 31.82 long). At
(2,30,8) both fillets turn tangent to the back face y=30, so the angle
between the chamfer's two faces goes to nothing there -- the spine's end
is a tangency extremity -- and a third face, the back face, is tangent to
both.

A fillet's section closes to the vertex at such an end; a chamfer's keeps
its width. The spine was not extended there, a chamfer's no more than a
fillet's, so the walk could not reach the back face's edges:

- the polygon block, its stripe walked backward to the vertex, stopped
  there, its last section at y=29.873, 0.127 short of the back face, and
  the corner bridged the gap with a patch whose three edges end 0.382
  short of their vertices: "valid", BOP's check clean, 11864.0665, where a
  fine mesh gives 11909.63;
- makeBox's, walked forward, ran on past the vertex on the guide's
  extrapolation and stopped 8e-5 short of the back face's edges, its
  last section in the back face but its ends on no edge: refused.

Upstream does the same, both ways (11864.0665 and refused; 11753.1281
with distances 1 and 1.5); a PartDesign Pad on MSVC gave the polygon's
three edges (11858.2585).

Now:

1. a chamfer's spine is extended at a tangency extremity too
   (`ChFi3d_ChBuilder::ExtentOneCorner`), and the walk runs on past the
   vertex either way until its sides step onto the back face's edges;
2. the stripe ends once both its sides are on the one face
   (`PerformSetOfSurfOnElSpine`). A side that reaches the back face first
   carries on over it, as a walk does across a tangent edge, until the
   other side reaches its edge; one more surface, between the face and
   itself, would only run on over the face (it ran down to z=0);
3. that end is its last section (`ChFi3d_PerformTangentEnd`, tried first
   at a vertex of one stripe). The section lies in the back face, the
   chamfer tangent to the face along it, so there is nothing to intersect:
   the cut is the surface's iso there, its curve on the face projected (in
   the face to 1e-7). The corner of the back face beyond the cut goes.

Both blocks give 11909.6170, the same faces. The back face loses the
triangle the cut takes off, 0.5 x 1.4063^2 (287.0112 of its 288), and the
chamfer meets it at 0 degrees along the cut. With distances 1 and 1.5,
either way round, one side reaches the back face first: the chamfer is
two surfaces, the second a sliver between the back face and the top
fillet, 11901.8128.

The chamfer sweep (`sweep/`, `OP=chamfer`: every edge at 0.3, 0.8 and 2,
every vertex's sets at 0.3 and 1), the library before against this one:

| | edge (3921) | vertex (12242) |
|---|---|---|
| loose -> ok | 6 | 28 |
| refused -> ok | 2 | 14 |
| invalid -> ok | | 13 |
| crash -> refused | 2 | |
| refused -> invalid | 2 | 2 |

All the cases that moved but one are #273's `Fillet001` (the handle's
chamfers along tangent chains that end where their faces turn tangent);
the one is #474's `Fillet003` `V1:2,6@1`. The four now invalid were
refused, and are a self-intersecting wire on #273's handle at 2 (`E11`,
`E30`; `V8:16,22@0.3`) and #474's at 1: FreeCAD rejects them as it did.
No result valid in both moved. `mini_ab_r3`'s `V1:1,3,6,11` came out
TIMEOUT; it hangs now and then with either library (a walk on a guide of
no length, `-6e-247..0`), refused the other times -- an uninitialized
distance, fixed in `c2635d5492` (next section).

Steps 2 and 3 are not the chamfer's alone: a fillet whose faces turn
tangent at its end stops there too. In the fillet sweep that moved only
#273's `Fillet001`, whose handle's fillets run out between its cylinder
and a face tangent to it to within its tolerance (0.71 at its vertices).
Edge `E22`/`E33` at 0.3 and 14 vertex sets with them lose a sliver,
0.0002 of area, that a stripe between the cylinder and itself left (4e-4
less volume, one face fewer); 13 vertex sets at 1, invalid (unorientable)
before, are valid. The last section there is only 0.0003 long, shorter
than its points' tolerances from the walk (3.5e-4), so the cut's two
vertices, 3.8e-4 and 4.4e-4, overlap: BOP's check reports 26 vertex
self-intersections at 0.3 and 28 at 1 where the input has 24 of its own,
and 20 edges too small where it has 16. The cut lies in the cylinder to
2.4e-7. Closing such a section to one point (both sides one DS point, the
end edge degenerate, as `PerformSingularCorner` does for a section of no
length) was tried at 0.3: 24 self-intersections and 18 edges too small,
but the side not at the point then ends 0.00033 from it, past the
loose-end check (the input's own widest gap is 2.6e-4) -- the section is
that long, and one vertex covers it only by its tolerance. Not kept:
neither is clean, and the input fails BOP's check itself. No other fillet case moved; the New draft sweeps
(1222 valid, 500 refused, 114 chains) are the same case for case. Suites:
fillet 585 + 5 XFAIL, draft 105, thickness 378 (plain, frozen).

| Case | What it covers |
|------|----------------|
| `chamfer_fillet_corner_poly`, `chamfer_fillet_corner_box` | x16win's case, both blocks: 11909.6170, no tolerance above 1e-4, BOP's check (loose, refused before) |
| `chamfer_fillet_corner_{poly,box}_1_1.5`, `..._1.5_1` | two distances, either way round: 11901.8128 |

## A chamfer corner of three with two chamfers on no common face (`c2635d5492`, 2026-10-16)

The chamfer sweep's `mini_ab_r3` `V1:1,3,6,11` -- four edges at the
vertex (38.5, 10.2, -9.75), three chamfers there -- hung about one run in
four, with this library and the one before; refused the other times, in
a second. A hung run was in `BRepBlend_Walking::InternalPerform`, its
`math_FunctionSetRoot` spending the time in SVD, on and on: the walk's
loop has no end when its step is NaN (never below the tolerance that
stops the halving, never at the bound). A trap in
`ChFiDS_Spine::SetFirstParameter` caught the spine's start set to `-inf`,
from `ExtentSpineOnCommonFace`, called by `ChFi3d_ChBuilder::
ExtentThreeCorner`.

`ExtentThreeCorner` extends each pair of the three chamfers on the face
the two have in common, by their distances on it, found by comparing their
faces. Two of the three here have no face in common, and their entries in
`dis[3][3]`, a local left uninitialized, kept whatever the stack held:
`-inf`, NaN, `-6e-247` -- or something the walk got through, the garbage
deciding. Now:

- such a corner is refused ("Chamfer corner of three: two chamfers on no
  common face"). Not extending that pair instead was tried: #962's like
  corners (`Chamfer` V33, V38; `Fillet` V35, V40, the four edges at a
  rib's foot) came out at 0.3 valid but with two self-intersecting edges
  in BOP's check, on clean inputs, and at 1 invalid;
- `ExtentTwoCorner` does not extend two chamfers with no common face (it
  did not already: their distances were 0, and 0/0 made no extension);
- `ExtentSpineOnCommonFace` does not extend by a distance that is not
  finite, and takes sin(alpha) from max(0, 1 - cos^2).

The chamfer vertex sweep against the library before: only such corners
moved, all to refused -- `mini_ab_r3` `V1:1,3,6,11` at 0.3 and 1 (TIMEOUT
before), #962 `Chamfer` V38 and `Fillet` V40 at 0.3 (valid, BOP-dirty as
above) and at 1 (invalid); their mirror twins V33 and V35 were refused in
that run. Fillets do not take this path. Fillet suite 593 + 5 XFAIL
(plain, frozen).

| Case | What it covers |
|------|----------------|
| `mini_ab_r3_chamfer_V1_{0.3,1}_{0..3}` | the corner, four times at each size: refused, and the run reaches its summary (it hung now and then) |

## Corner plates held to their own miss (realthunder/FreeCAD#631, #273, 2026-10-16)

The largest class of the results BOP's check reports on clean inputs
(above, "The sweeps") is corners at loose tolerances: two edges too small
and two vertices self-intersecting, in some 41 vertex cases of #631's
four inputs, #962, #273 and #474's `Fillet002`. #631's `V8:9,21` at 0.3,
two fillets with no face in common: the plate is 1.9e-4 off its boundary
(`G0Error`), its approximation 1.3e-3 off the plate, and the corner's
face and so its edges and vertices at 3.1e-3 -- over a side 0.0025 long,
the edge between the fillets' other faces. BOP's check found that edge too
small under the tolerance and its two vertices overlapping.

`PerformMoreThreeCorner` held an ordinary corner's approximation to ten
times the plate's miss, in at most 9 patches, and gave the face the
approximation's error to the plate as its tolerance; only a setback
corner was held to the miss itself, in 16, its face at the criterion
(the fit to the boundary, which the curves' tolerances carry). Now every
corner is held to the miss, an ordinary one in up to 32 patches, and every
corner's face takes the criterion. On ten of #631's dirty corners: 6
clean of 0, `V8:9,21` at 6.5e-4; 0.40 s to 0.63 s; at most 1936 poles
for 256. The face's tolerance alone, the approximation as it was, made
one clean; 20 points on the boundary in place of 4 made more of them
worse; twice the miss, worse than once.

The face's tolerance had been covering a gap, at #273's fillet of 0.3 on
its edge 5: the corner's vertex 0.029 from the end of the circle beside
it, an edge of tolerance 1e-7. ShapeFix's `SameParameter` pass, the last
on the new faces, raises a vertex to its edges' curve ends but not the
edges with it; the pass that raises an edge to the end of its curve
(`ChFi3d_EdgesCoverTheirEnds`, "An edge's tolerance over its curves on
the faces", above) had already run -- and found the vertex short of the
gap, where before the face's 0.045 had raised it in time. The pass now
runs again after ShapeFix's: 12 of #273's results loose without it (the
loose-end check, 0.029 and 0.018), none with it.

Still reported, each for its corner's shape, not for slack left in it:

- #631's `V7:8,18` and `V14:22,28` at 1 (three self-intersecting edges
  and a vertex). Of their two corners the one of a single fillet falls
  back to G0, 0.042 off a boundary that closes to 1e-13 -- not what BOP's
  check finds. The corner of two holds 0.063 of the sharp edge on its
  floor, and the next side, of radius about 1, leaves it tangent: a
  boundary turning through no angle, the arc 0.002 off the edge's line
  (0.063^2 / 2r) where it passes the edge's vertex, under the corner's
  tolerance of 0.0077 (vertex 0.0154). Held to 1e-3 x r it would part;
  the plate does not get there -- degree 2 or three iterations bring the
  single corner to 0.015 or 0.010, the double to 0.00044 but its
  approximation 0.18 off it inside, and the check reports the same.
- `V1:2,5` and `V7:9,16` at 0.3: a side 0.004 and 0.007 long between the
  two fillets' ends, its vertices 0.0045 and 0.0079 apart at tolerances
  0.0035 and 0.0054 each -- twice the edges', a point taking the plate's
  error once from each curve it ends. At once, they would part; the edges
  either side of the short one, converging on it, would still come within
  0.001 and 0.0034 of each other. The class of a corner with a side too
  small (a setback blend, or the side closed to a point, not tried here).

The sweeps against `a2f5c2a5d4`'s baseline: no valid result lost. Edge 16
`LOOSE` -> ok, vertex 112 and 4 refused -> valid (#876's four-edge
corners at 0.3); 17 edge and 97 vertex tolerances below half; volumes
within 0.078, #273's loose corners. BOP's check (the cases the old
baseline had valid): vertex 37 reported -> clean, edge 1, none the other
way; #273's `V4:4,5,11,14` at 1 outlasts the 120 s now (reported
before). Chamfers, before and after: edge 1 and vertex 36 `LOOSE` -> ok;
#273's E12 and E16 at 2 from 3.11 to 0.718, E16 now its siblings'
volume (8533.30; E14 8533.29). New draft sweeps the same. The suite's
`slot_by_slope_all_four_r1.5` met the refined shape's plate, a corner of
17 faces to its 18, 0.0999 apart while the refined one stood at 0.156;
at 0.016 they are 0.109 apart, and the margin is now 0.1 x r past 1 (the
gap grows with the radius: 0.034, 0.070, 0.109). Nothing to picture: the
corners look as they did.

| Case | What it covers |
|------|----------------|
| `issue631_corner_plate_e{9_21,1_8,15_16}_r0.3` | #631's corners of two fillets: valid, the volume, a tolerance of 1e-3 (9, 21) or 0.02, nothing for BOP's check |
| `issue273_corner_circle_end_e5_r0.3` | #273's edge 5: the volume within 0.02 (MSVC's is 0.0077 off, as it was 0.01 before), no loose end (no `max_tol`, which would allow it) |

## A drafted boss flush with the plate's side (2026-10-17)

The flush boss of "A boss flush with the plate's side" drafted: a cone,
radius 5 at the foot to 4 at 10 up, on the plate (30 x 20 x 3) with its
foot circle touching the plate's top edge at (15,0,3). The cone touches
the side's plane only there; above, it leans in. A fillet round the foot
was refused at every radius, as the cylinder's was before `b234546fbe`
("TopOpeBRepDS_DataStructure::Point"), and that fix did not take it: its
two ends' lines on the boss, run on, never touch the side.

What the result is to be, by the same construction: the fillet made on a
plate reaching past the side, then cut by the side's plane. Here the cut
does not reach the fillet's line on the boss. It rises from the fillet's
point on the plate's edge on one side to an apex below that line -- 3.575
up at radius 1, the line at 3.90 -- and comes down to the other side's
point. The fillet stays one ring: its line on the boss closed all round,
a band of it running over the apex, its lower edge notched by the cut.
The side grows a bump under the cut, bounded by the plate's top edge.

`PinchGap` in `ChFi3d_Builder.cxx`, tried by `PerformPinchEnds` when an
end's line does not touch the side. The stripe ends where it does, each
end its section across the fillet's surface (an iso of the torus, from
the point on the plate's edge to the point on the boss). The gap between
the two ends is closed by a face of the first end's surface run on, in
the DS as a corner's surface: bounded by the two sections, the line on
the boss run on across the gap (on the boss's face too), and the side's
cut (on the side's surface, untrimmed), found at 81 steps across the gap
-- at each a root from the line on the plate, outside the side past the
ends, toward the line on the boss, inside it all the way -- and
interpolated, with its curves on both surfaces. Its orientations are
`ChFi3d_FilDS`'s for a surface data running from the last end's section
to the first's: its lines those of the first end, the cut in the place of
the line on the plate (its transition on the side the plate's composed
with the two faces' orientations). Made only so:

- the fillet's surface periodic, its lines along u and its sections isos
  of it, the two ends on one surface (the torus round a cone on a plane;
  a chamfer's cone the same);
- the gap under half a turn;
- the line on the boss inside the side all across, the line on the plate
  outside it between the ends: a boss leaning out (a cone widening
  upward) crosses the side and is refused, as before;
- the side's surface elementary, its seam not through the vertex.

Checked against the construction (`drafted_csg` in the suite): valid,
BOP's check, nothing of either outside the other, within 1e-3 of the
volume. At radius 3, drafted 0.6 deg, every point sampled on either lies
on the other within 3e-8, and the bump's area (12.75122, by polygon)
agrees to 8e-6; the volumes there differ by 0.014 with the cut's
parameters (0.028 at 41 points), the integration over the B-spline
boundary, and the side face's area by 0.0097 the same way. The cut's
tolerance is 1e-6 to 6e-6 (81 points; 41 left 1e-4 at radius 4). A
chamfer is made the same way and matches: its cut does not reach its line
on the boss, so the corner of no angle that refuses the flush boss's
chamfer does not arise.

Not this: #876's post, whose drafted corners (cones of 1 deg) stand flush
with the plate's rounded corners along an arc of the foot -- the foot in
two edges there, one on the plate's top, one shared with the plate's
corner cylinder -- not at a point. A fillet of the foot along the plate's
top (`issue876_Fillet` edges 30 to 32, a chain) ends at the vertex where
the foot leaves the top, and carried on, the band between the side's cut
and the line on the post would run on along the whole flush arc: no other
end to close against. Still refused (the sweep's `E30`, `E31`, `E32`).
The README had called that post this case; it is not. Also still
refused, the cylinder's as well: the boss's own seam through the tangent
point, and a foot in two equal halves, the seam opposite the point
(neither reaches `PerformPinchEnds`; the halves are made since
`892a10b753`, "A walk past a closed spine's end", below, the seam through
the point since `e549e29656`, "The boss's seam through the point").

The sweeps: fillet and chamfer, edge and vertex, no case moved (status,
volume, faces); New draft's the same. BOP's check now runs the cases
`6de00fea30` made valid, which its baseline had skipped as `LOOSE`: 60
vertex and 8 edge more. #876's four-edge corners at 0.3 report an edge
crossing itself in 51 of their 56 vertex cases and 7 of 8 edge (`E37`,
`E50`, `E52`, `E58`, `E62`, `E66`, `E69`, tolerance 0.00524); #273's
`V9` to `V12` at 1 come clean. The same with the library before this
change: a matter for those corners, not the gap. The BOP baselines
record them. (Not the corners' either: the next section.)

| Case | What it covers |
|------|----------------|
| `boss_drafted_flush_foot_r{0.3,1,2,4}` | the foot at four radii: against the construction, as above (refused before) |
| `boss_drafted{4.9,3}_flush_foot_r1` | drafted 0.6 deg (volume within 0.01: the integration, above) and 11 deg |
| `boss_drafted_turned_foot_r1` | the cone's seam on the far side |
| `boss_drafted_chamfer_r1` | the foot chamfered |
| `boss_drafted_foot_and_top_r1` | the foot and the boss's top edge together |
| `boss_drafted_two_feet_r1` | two drafted bosses on one side |
| `boss_drafted_rim_foot_r1` | against a round plate's rim from inside: the side a cylinder |

## A fillet split only where its section is a point (realthunder/FreeCAD#876, 2026-10-17)

The reports of the section above, #876's at 0.3, were not the corners'.
#876's post stands flush with the plate's sides, its walls -- planes along
the long sides, cones at the corners -- drafted a degree, and a fillet of
its foot at 0.3 is 0.005 wide all along. Upstream refuses those edges ("no
suitable edges"); the fork makes them, and the result was valid, but BOP's
check found an edge crossing itself, and the result's tolerance was
0.00524. Edge 52 (the long side's, two planes): the walking gives one
surface data over the whole edge, and the fillet came out in three faces,
cut at x = 4.04 and 9.14, each cut one vertex where both of the fillet's
lines meet, 0.0026 from each.

`ChFi3d_FilBuilder::SplitSurf`. A fillet narrower than 100 times the
approximation tolerance (`GetMinimalDistance`) is searched for a section
closing to a point -- a fillet between two faces that touch along a curve
-- and split there, the section made one vertex, the sides' lines meeting
in it (its tolerance the section's length). The search solves
`ChFi3d_SearchSing` for zero: V.(P2 - P1), half the derivative of the
section's squared length. A root was taken for a point if that function
was below tolapp3d there -- true of every root it had found. A fillet of
near constant width has minima of no depth along it, and each one was
split at. Now the test is the section's length at the root, below
tolapp3d. Edge 52 comes out one fillet face, its edges at 1.5e-4, BOP's
check clean, the same volume (8665.783943).

`b4f2f7592c`. The sweeps: only #876's at 0.3 move, edge 16 and vertex 112 --
`Fillet` and `Fillet001`, edges 10, 37, 50, 52, 58, 62, 66, 69 and their
vertex cases -- the volume within 8e-4, one to ten faces fewer, the
tolerance 0.00524 -> 1.2e-4 to 2.9e-4. Two of the four-edge corners
(`V4:2,4,10,30`, `V37:47,48,50,93`) stay at 0.0192, their corners'. BOP's
check: 7 edge and 49 vertex cases reported -> clean, all those of the
section above; the two corners keep an edge too small and a vertex there.
The chamfer sweeps and New draft's are the same.

| Case | What it covers |
|------|----------------|
| `issue876_kink_e{52,50,58}_r0.3` | the long side's foot (two planes) and two corners' (a cylinder and a cone): one face, BOP's check |
| `issue876_corner4_r0.3` | now held to 1e-3 and BOP's check (0.00524 and a too-small edge before) |
| `issue876_post_foot_e10_r0.3` | now held to 1e-3 (0.00524 before) |

## A walk past a closed spine's end (2026-10-17)

The flush boss turned a quarter, its seam opposite the tangent point: the
foot in two equal halves, from the point to the seam and back. Refused at
every radius ("PerformSurf : Failed approximation!"), the cylinder's and
the cone's, where the boss turned any other way but through the point is
made. So was the rim's boss with its seam opposite the point.

The foot's spine is closed, both ends at the tangent point. Each edge's
fillet is a torus (KPart) from where its line on the plate leaves the
plate's top at the side, 2.93 from the point at radius 1; the walk does
the rest on each side, the plate's top run on as a plane past the side
(`ChFi3d_BuildPlane`, `intl` 5). Forward from 28.49 the walk crosses the
point at 31.42 and runs on round the spine again, as far as the
extension lets it -- half the spine past the end, which with equal halves
is exactly the seam at (15,10). It stops there on the cylinder's
restriction, the seam edge, and the walk gives that last point the
guide's parameter of the spine's end, 31.42, after its neighbour's 47.23.
The line is out of order, and its approximation fails. At a turn of 0
the walk's line comes back ending free, and `ComputeData` cuts a line
that is all extension back to a third of the way from its end: to
35.66, past the side by 1.3, which is what `PerformPinchEnds` needs
(the walk had gone on to 39.25, the seam there being at 39.27).

`ChFi3d_Builder::ComputeData` (`ChFi3d_Builder_6.cxx`), after the walk:
an end point whose guide parameter runs back past its neighbour's is
dropped, while the line keeps more than two points, and the line's
extremities at that end made the free ones of the point before it. A
line cannot run backward, so no other line is touched; this one then
ends free, and is cut back as above. The halves come out at the
volumes of the boss turned any other way, to the digit: cylinder 2585.9842,
2591.8420, 2611.2741, 2691.5445 at 0.3, 1, 2, 4; cone 2439.2554,
2443.9037, 2459.2745, 2522.2233; the rim's boss 4561.6566. Valid, BOP's
check clean.

Still refused: the boss's seam through the tangent point (a turn of
three quarters), cylinder and cone, fillet and chamfer -- the foot one
closed edge there (made since `e549e29656`, the next section) -- and the
rim's own seam through it (`boss_rim_seam_foot_r1`).

`892a10b753`. The sweeps do not move, line for line: fillet edge and
vertex, BOP's check, the chamfer sweeps and New draft's. The fillet suite
616 + 4 XFAIL, frozen and not; draft 105, thickness 378.

| Case | What it covers |
|------|----------------|
| `boss_flush_halves_foot_r{0.3,1,2}` | the foot in two equal halves, the boss's seam opposite the point: the volumes of `boss_flush_foot_r*` (refused before) |
| `boss_drafted_halves_foot_r1` | the drafted boss the same, against the construction |
| `boss_rim_halves_foot_r1` | the rim's boss with its seam opposite the point (refused before) |

## The boss's seam through the point (2026-10-17)

The flush boss turned three quarters: its seam runs up from the tangent
point, along the line where the boss touches the side's plane, and the
foot is one closed edge, its vertex at the point. Refused at every
radius, cylinder and cone, fillet and the cone's chamfer.

Two things. The walks past the stripe's two ends (as in the section
above, on the plate's top run on as a plane past the side) each stop on
the boss's seam, where the seam's line lies at the spine's end. The
surface each made is all on that plane, and `ChFi3d_Purge` removes such
a surface data when its other side ends free -- at any other turn it
does -- but keeps it, shrunk to its line on the boss, when that side ends
on an arc: here the seam. The stripe then ended in a surface data with
both ends on arcs, which `PerformPinchEnds` does not take. A seam is no
end of its face: the walk only stopped where its parameters do. The
purge now treats an end on the other face's own seam as free.

Then the result: the pinch point, (15,0,4) at radius 1, lies on the
seam, and the seam was left whole, from the foot to the top; the
cylinder kept its foot circle and came out unorientable. The seam is now
split at the point, its stretch from the vertex up to the point under
the fillet (`PerformPinchEnds`). The drafted boss's gap
(`PinchGap`) crosses the seam halfway between the fillet's ends instead:
the boss's line run on is cut in two there, the half past the period
given its pcurve on the cone a period back, and the seam split at the
crossing. Both refuse when the point is off the seam by more than ten
times the tolerance.

`e549e29656`: `ChFi3d_Builder_2.cxx` (`ChFi3d_Purge`), `ChFi3d_Builder.cxx`
(`PerformPinchEnds`, `PinchGap`). The volumes of the boss turned any
other way, to the digit: cylinder 2585.9842, 2591.8420, 2611.2741,
2691.5445 at 0.3, 1, 2, 4; cone 2439.2554, 2443.9037, 2459.2745,
2522.2233; the cone's chamfer 2453.7582. Valid, BOP's check clean. The
cylinder's chamfer stays refused (`boss_flush_chamfer_r1`), the rim's
own seam through the point too (`boss_rim_seam_foot_r1`).

The sweeps (sweep/README.md) move two cases, both made now and refused
before: `issue273_Fillet V5:5,6` at 0.3 and 1, the two arcs of a
cylinder's rim at a corner. The walk along the rim ended on that
cylinder's own seam and is cleaned away now, not kept -- the purge's
half at work away from any boss; valid, BOP's check reporting what the arc E5 filleted
alone gets there (baseline/bop_vertex.txt). Every other case the same,
the BOP and chamfer sweeps and the draft sweeps too; the suites here,
draft and thickness pass.

| Case | What it covers |
|------|----------------|
| `boss_flush_seam_foot_r{0.3,1,2,4}` | the boss's seam through the point: the volumes of `boss_flush_foot_r*` (refused before) |
| `boss_drafted_seam_foot_r{0.3,1,4}`, `boss_drafted_seam_chamfer_r1` | the drafted boss the same, fillet and chamfer, against the construction |

## A fillet run on past its vertex (realthunder/FreeCAD#273, #474, 2026-10-18)

#273's E5 and E7, the arcs of the cylinder's rim under the handle's front
and back, are filleted between faces 1.6 deg from tangent: a strip 0.009
wide at 0.3. Upstream refuses them ("no suitable edges",
`PerformElement` taking the faces for tangent at 0.1 rad; 0.001 here
since `b096b91e74`). Made here, valid, but BOP's check found faults in
five of the six (radii 0.3, 0.8, 2): edges crossing themselves, up to 14,
and at 0.3 a face (E7 at 2 clean). At the strip's end four sharp edges meet
(`PerformIntersectionAtEnd`). The walk runs past the vertex as far as
`ExtentOneCorner` carries the spine, half the edge, 5.7. The line on the
handle stops on its edge at the vertex, but the line on the cylinder,
0.004 under the rim and along it, meets no edge and runs on to the walk's
end. That corner (`PerformMoreThreeCorner`) is cut by the rim's ledge
along the strip, not across it, and runs off the surface's end rather
than to a line: the ledge made again over 7.0 of its area, an edge of
0.029 closing it to the rim (sweep/README.md, the edge triage).

The end now refuses a fillet that has one side on an edge of the vertex
and the other side run on, free, farther from the vertex than ten times
the fillet's width there (the distance from the end on the edge to the
other line). Measured over the suite and both sweeps on every case that
ends on one arc: up to 2.4 times otherwise, and from 34 (#273's E7 at
radius 2) to 1085 (E5 at 0.3) on the run-on ones -- #273's E5 and E7 at
every radius, and #474 `Fillet003`'s E2 and E18, the same kind of edge
(between two faces 1.5 deg apart), which came out invalid or refused. A cap across the strip in its section at the vertex, 0.009
wide, would be the corner they want; the builder has no form for it.

A refused corner goes to the setback fallback (FreeCAD's
`FilletCornerSetbackFallback`, `ComputeSetbackFallback`), which sets it
back from the vertex and makes it again: #474's E2 and E18 come out
valid and BOP-clean at every radius, #273's E5 and E7 at 0.8 and 2 too.
At 0.3 #273's are still reported, less: the corner's section edge is
0.0105 long, its vertices 0.0092 loose (Edge/TooSmallEdge, Vertex/
SelfIntersect), no face crossing itself. With the fallback off they are
refused, upstream's answer.

`95a3e143e1`: `ChFi3d_Builder_C1.cxx` (`PerformIntersectionAtEnd`). The
sweeps (sweep/README.md) move only these edges and the corners holding
them: edge 5 and vertex 9 results of #474 invalid -> valid, BOP's check
clean on all 14; vertex 5 invalid -> refused (#273's `V5:5,15` and
`V7:7,11` at 0.3 and 1, #474's `V10:18,24` at 1); 6 edge and 34 vertex
results of #273 moved by thousandths of volume, BOP's check now clean on
3 edge and 15 vertex results it reported; the other 20 report only
small edges and their vertices, 19 of them results it found edges or
faces crossing themselves on before. Clean to reported: none. The BOP, chamfer and New draft sweeps otherwise the same,
line for line; the fillet suite 629 + 4 XFAIL, frozen and not; draft
105, thickness 378.

| Case | What it covers |
|------|----------------|
| `issue273_rim_run_on_e{5,7}_r2` | #273's rim arcs, the corner set back: valid, BOP's check clean |
| `issue474_f003_run_on_e2_r0.3`, `issue474_f003_run_on_e18_r0.8` | #474's step edges, invalid before: valid, BOP's check clean |
| `issue273_rim_run_on_e5_r0.3_no_fallback` | with the fallback off the fillet is refused |

## A set back corner that folds (realthunder/FreeCAD#273, 2026-10-18)

#273's handle has a triangular pocket in its top, 1 deep, its apex 22
deg. A fillet of 0.8 on either rim (E23, E24) ends at the apex, where the
other wall stands across its end. At 0.3 the end is a cap in that wall's
plane, run on past the apex by 0.8 (upstream's result, BOP's check
clean). At 0.8 the cap would run 2.1 past the apex, off the top: the top's
outer edge is 1.3 from the apex. The corner fails, upstream refuses the
fillet, and here the setback fallback set the corner back by the radius
and made it as a patch of four sides: the fillet's section, the top's
line, the wall's line on to the apex, and a cut down the other wall. The
top's line crosses the pocket from one rim to the other, and the patch,
from it down to the apex at the wall's line, reaches under the top and
across the apex: valid, and folded over itself (BOP's check:
Face/SelfIntersect, four lines 0.3 long on the patch, on two sheets).
#273's `Fillet001`, the same handle with the pocket's edges filleted,
did the same on its rims at 0.3 (E39, E40), alone and with the edges at
their ends.

The setback fallback (`ComputeSetbackFallback`), and the longer
extension tried after it (`ComputeLongExtension`), took a result that was
valid, had every fillet in it and no edge too loose; they now also want no
face of it folded. A face is looked at if the computation made it (not on
a surface of the input), it is not elementary (BOP's check skips planes,
cylinders, cones, spheres and tori that do not cross themselves), and it
lies within the setback and twice the radius of a vertex set back
(anywhere, for the longer extension). It folds if `IntTools_FaceFace` of
it with itself, as BOP's check computes it, finds a line longer than 1e-4
whose middle is at two places in (u, v). The length is not scaled to the
face's tolerance: `Fillet001`'s loose input leaves its patch at 0.038,
and the lines there are 0.13 long. #962's corner `V48:67,120` at 0.3 is
made as before: the line found there is a point at the plate's pole, at
one place in (u, v) (sweep/README.md).

A folded corner is refused at its step and the fallback goes on to the
next. On these none comes out unfolded, and the fillet is refused, as
upstream refuses it.

`31cf3ce134`: `ChFi3d_Builder.cxx` (`HasFoldNear`). The sweeps
(sweep/README.md) move only these: edge 4 results made -> refused (#273's
`E23` and `E24` at 0.8, `Fillet001`'s `E39` and `E40` at 0.3), vertex 10
(`Fillet001`'s corners `V23`, `V24` and `V25` holding `E39` or `E40` at
0.3), and in the BOP sweep only `E23` and `E24`, reported before; no
other result BOP's check reports changed. The chamfer and New draft
sweeps the same, line for line; the fillet suite 632 + 4 XFAIL, frozen
and not; draft 105, thickness 378.

| Case | What it covers |
|------|----------------|
| `issue273_pocket_apex_fold_e{23,24}_r0.8` | the pocket's rims at 0.8: refused, not folded -- made since `efd99a29b5`, the next section, and the cases renamed `issue273_pocket_apex_off_*` |
| `issue273_pocket_apex_cap_e23_r0.3` | at 0.3 the cap in the other wall, BOP's check clean |

## A cut that runs off the face (realthunder/FreeCAD#273, 2026-10-19)

The pocket in #273's handle is a triangle 1 deep, its apex 21.9 deg; its
rims are E23 and E24, its base E22. Past the apex the top runs on 1.30,
along the other wall's line, to the handle's end: a B-spline face, its
edge on the top an arc of radius 16.3 (E17). A fillet on one rim ends at
the apex, a vertex of three edges, and the corner (`PerformOneCorner`, the
end OnSame) caps it in the other wall's surface carried on past the apex:
the cap runs r / sin(21.9 deg) past it, 0.81 at 0.3. From 0.49 it runs
past the top's edge: the fillet's line on the top, carried on past the
apex, ends on E17 before it reaches the wall's surface. The corner had no
cap for that ("bouchon non ecrit") and the fillet was refused, as upstream
refuses it; the setback fallback made a patch that folded, refused since
the last section.

Such an end -- the line on the top ending on an edge of the top that is
not the vertex's -- is now carried on into the face beyond that edge (the
handle's end, `Fob` in the code):

- P, where the fillet's surface, the wall's surface and the end's surface
  meet, by Newton's method from the line's end; it must lie on the end
  face, under the top by more than 1e-6, and off the wall's own face;
- the cut on the wall's surface from the corner's point on its edge to P,
  and on the end face from P to the line's end on E17;
- the wall's surface carried on meets the end face from P to R, where E17
  crosses the wall's surface; the wall's edge on the top is carried on to
  R; E17 is cut at R and at the line's end, and between them lies under
  the fillet.

The groove the fillet leaves runs out through the handle's end, closed by
the cap in the other wall. The curve from P to R is short just past 0.49
(2e-4 long at 0.5) and fails as an intersection there; it is then the
segment, which lies on both surfaces within 1e-7. The new edges' sides:
at the cut, the cap lies the way of the fillet's outward normal and the
end face's part kept the other way -- which way the normal runs, the piece
on the wall says, whose orientation the corner finds as before; across P
to R, what is kept of the wall lies inside the end face and what is kept
of the end face outside the wall's plane.

Each single rim's result is the input less the strip between the rim's
two faces and the fillet's cylinder, cut by the two walls' planes at its
ends -- made by booleans, to within 5e-4 of the volume:

| r | booleans | fillet |
|---|----------|--------|
| 0.3 (the cap on the top) | 8559.3262 | 8559.3262 |
| 0.49 | 8559.0558 | 8559.0558 |
| 0.5 | 8559.0377 | 8559.0377 |
| 0.55 | 8558.9419 | 8558.9416 |
| 0.7 | 8558.5962 | 8558.5962 |
| 0.8 | 8558.3169 | 8558.3169 |
| 0.95 | 8557.8240 | 8557.8240 |

E24 gives E23's volumes, E22 with either rim the same pair's. E23 with
E24, alone or with E22, were made before -- the apex a corner of two
fillets -- and are unchanged. At 1 every one is refused: the pocket is 1
deep, the fillet's line on the wall would lie on the floor's edge, and the
walk does not start ("StartSol echec") -- a fillet as wide as its face,
not this corner. 0.487 is refused too: within 0.001 of the radius at which
the cap just reaches E17, P lies on the top.

A chamfer's end there is the same corner, and is made from 0.5 to 0.95 as
well, refused before: each single rim's volume is the input less the
triangle between the rim's two faces, cut the same way, to 1e-4 (8558.4246
at 0.5, 8556.6985 at 0.8, 8555.5202 at 0.95), E22 with E23 at 0.8
8555.5159; all clean by BOP's check. E23 with E24 chamfered is refused
before and after -- the corner of two chamfers, not this one.

The sweeps (`efd99a29b5` against `31cf3ce134`) move on #273's E23@0.8 and
E24@0.8 alone, refused before -- the fillet sweep's and the chamfer
sweep's, the fillet's results clean by BOP's check; the vertex sweep's
radii, 0.3 and 1, are below and at the range made. The draft sweeps and
the suites are the same.

| Case | What it covers |
|------|----------------|
| `issue273_pocket_apex_cap_e23_r0.3` | the cap on the top, as upstream's |
| `issue273_pocket_apex_off_e{23,24}_r0.8` | the cut off the top, into the handle's end |
| `issue273_pocket_apex_off_e23_r{0.5,0.95}` | near the change (the segment from P to R) and near the wall's depth |
| `issue273_pocket_apex_off_e22_e23_r0.8`, `issue273_pocket_apex_off_e22_e24_r0.6` | with the base filleted too |
| `issue273_pocket_apex_off_chamfer_e{23,24}_r0.8`, `..._e23_r{0.5,0.95}`, `..._e22_e23_r0.8` | the chamfer's end, the same corner |

## The end flat at a vertex (an option, realthunder/FreeCAD#273, 2026-10-19)

The groove of the last section runs out of the pocket, and upstream's at
0.3 does too, only less far: a fillet that ends at a vertex is closed by
the face at the end, carried on as far as the fillet's section reaches,
and at a pocket's acute tip that face meets the fillet's line on the top
only past the tip. The cut fills the mirror image of the tip beyond it,
r / sin(22 deg) long. The same happens, shorter, at the pocket's base
corners (79 deg): the base's wall carried on past them, 0.19 r.

`ChFi3d_Builder::SetFlatEndAtVertex(true)` ends such a fillet flat
instead (`MakeFlatEnd`, `ChFi3d_Builder_C1.cxx`): in the plane through the
vertex and the fillet's point on the edge it ends on -- the pocket's corner
edge --, as square to the spine as that edge allows; here, square to the
rim. The face it leaves is the groove's own section: between the
fillet's section, the corner edge's piece above the point, which the
other wall keeps, and the line on the top from the vertex to the fillet's
line. Nothing past the vertex is cut, and the cap no longer runs off the
top, so 0.487 is made as well. It applies at an OnSame end, at a vertex of
three faces, where the fillet's line on its other face, along its tangent
at the end, meets the face at end's edge on that face behind the vertex
and past the vertex's section along the spine: the usual cap would land
past the vertex, as it does where the open corner between the spine and
that edge is under 90 deg. Wider, the cap leans back over the fillet and
cuts nothing past the vertex; at 90 deg the face at end is square to the
spine already; either way the end is the usual one. (A first test that
asked only for the edge's side made 13 of the edge sweep's results
invalid and cut more than the usual end at others: #631's fillets ending
on a curved face, #309's, #474's corner of 90 deg.) Where the face cannot
be made (the corner edge not in the plane, the line on the top not
straight near enough, the section not computed) the end is the usual
one.

The setting is off by default, as upstream, and the calling thread's own;
`ChFi3d_SetFlatEndAtVertex(int)` is its C function, for callers that look
it up at run time, and `../flat_end.py` reaches it from Python. Two static
functions and a C function are all it adds: no upstream symbol is missing
and `ChFi3d_Builder`'s layout is upstream's (816 bytes). FreeCAD's Part and
PartDesign Fillet turn it on from their `_Version` 1, which a new object
gets; a file's Fillets from before keep their shape.

Each single rim's result is the input less the strip between the rim's
two faces and the fillet's cylinder (the chamfer's triangle), from the
apex to the base corner, cut square at both -- made by booleans, to the
digit:

| r | booleans | flat | the usual end |
|---|----------|------|---------------|
| 0.1 | 8559.4677 | 8559.4677 | 8559.4675 |
| 0.3 | 8559.3297 | 8559.3297 | 8559.3262 |
| 0.487 | 8559.0759 | 8559.0759 | refused |
| 0.5 | 8559.0538 | 8559.0538 | 8559.0377 |
| 0.8 | 8558.3813 | 8558.3813 | 8558.3169 |
| 0.95 | 8557.9287 | 8557.9287 | 8557.8240 |
| chamfer 0.5 | 8558.4805 | 8558.4805 | 8558.4246 |
| chamfer 0.8 | 8556.9137 | 8556.9137 | 8556.6985 |

E24 gives E23's. E22 with either rim: its own end at the other base
corner flat too. E23 with E24: the apex is a corner of two fillets, as
before; their ends at the base corners are flat. All three: no end is a
single fillet's, nothing changes. At 1 the fillet is refused still.

E22 alone, the base rim between the two 79 deg corners, is the input
less its strip as well: 8559.4260 at 0.3, 8559.0661 at 0.8, against
8559.4255 and 8559.0566 for the usual end.

The sweeps (`cd24623b20`, on FreeCAD's build of Thundereal's main) with
the option off are the baselines', to the last result, the fillet's edge
and vertex sweeps alike. With it on (`FLAT=1` in the sweep's environment,
read by `fsw.py` and `fsw_bop.py`), the edge sweep moves on #273's three
rims at 0.3 and 0.8 alone, each by its groove past the vertex, two faces
more (the flat ends), and every one clean by BOP's check; the vertex sweep
on the corners of those rims. Fillet001's E39 at 0.3, refused without it,
is made, 8534.9992, matching the booleans within 2e-4 -- the input is not
clean by BOP's check itself. The suites -- the fillet's, plain and frozen,
the draft's and the thickness' -- pass, the option off in all but these
cases.

| Case | What it covers |
|------|----------------|
| `issue273_pocket_flat_e23_r{0.1,0.3,0.487,0.8,0.95}`, `issue273_pocket_flat_e24_r0.8` | the end flat at the apex and the base corner, from small to near the wall's depth; 0.487 refused without it |
| `issue273_pocket_flat_e22_e23_r0.8`, `issue273_pocket_flat_e23_e24_r0.8` | with the base; with both rims, the apex a corner of two |
| `issue273_pocket_flat_chamfer_e23_r{0.5,0.8}` | the chamfer's |

## The end through the faces past a vertex: two pieces turned (2026-10-19)

Two faults of `PerformIntersectionAtEnd`, the end of a fillet at a vertex
of four edges or more, or whose line runs onto more than one face there.
Both came out invalid with upstream's files as well.

**A piece of an edge from the vertex to the line's end** (`6fd966afde`).
Where the fillet's line on one face ends on an edge of the face beyond
(`oneintersection`), the piece of that edge from the vertex to the line's
end bounds the cut, and is turned on the face at end to follow the cut on
from the end they share. That end was the first pairing of ends within
`tolpt` (1e-4), and with none within it the piece was turned regardless.
The cut is computed on the face at end carried on and can end farther
than that from the point on the edge. #273's handle stands on the cup's
top, its front and back on the cup's rim, carrying the cup's wall on (a
cone about the axis, 16.75 at the rim, 16.296 at the handle's top): the
fillets of its sides' feet (`E11`, `E15`) end there, the cut 0.003 from
the rim point, and the piece of the rim came out the wrong way round in
both its faces (`BadOrientationOfSubshape`), at every radius. The nearer
pairing of ends decides now. Each result is the input fused with the
strip between the faces and the fillet's cylinder, cut to that cone: BOP's
difference between the two, both ways, is empty. (The volumes are not the
measure here: integrated adaptively they move by up to 0.1 from the plain
integration, the faces at 0.03 to 0.19 of tolerance.)

The sweeps (`6fd966afde` against `cd24623b20`): the fillet's edge sweep
turns 9 invalid results valid (`E11`, `E15` and `Fillet001`'s `E16`, at
0.3, 0.8 and 2), the vertex sweep 18, and makes 4 refused (`V5:5,15`,
`V7:7,11` at 0.3 and 1; at 0.3 not clean by BOP's check, as `E5` and `E7`
alone are not); the chamfer's edge sweep turns the same 9 valid. Nothing
else moves, and the suites are the same.

**The piece of a cut edge kept** (`5fe644b95d`). A face the cut passes is
bounded by an edge the cut crosses, and the piece of it on the vertex's
side is under the fillet: the side was the one of the edge's end on one
of the fillet's faces, and where both ends were on them, on the same one,
the end nearer the vertex. #474's `Fillet002` has a sliver of a top beside
its upright edge (13 high): its edge on one of the fillet's faces is 0.155
long, its long edge's other end on the other face 2 away, so both ends
were on the fillet's faces, one on each, and the first test chose the far
end. The fillet at 0.3 and 0.8 (its line on the narrow side runs on below
the top, onto the faces past it) kept the 0.035 of the long edge by the
far vertex and the short edge, and lost the rest: the top open, the
corner left in it. The nearer end decides whenever both are on the
fillet's faces. The volumes are the input less the strip between the two
faces and the fillet's cylinder by booleans, to the digit (the strip,
carried on through the body, also cuts four slivers out of the steps
above, 0.00377 each at 0.3 and 0.14648 at 0.8, which the fillet rightly
leaves).

The sweeps (`5fe644b95d` against `6fd966afde`): the edge sweep turns
#474's `Fillet002` `E11` at 0.3 and 0.8 valid, the vertex sweep ten sets
with it, the chamfer's edge sweep the same two; nothing else moves, and
the suites are the same.

Of the fillet edge sweep's 21 invalid results, 11 are valid now. Left:
#273's `E38` at 2 (the flat face a segment 1.4 wide, the fillet wider than
it), `E20` at 2 and `Fillet001`'s `E55` at 2 (inputs not clean by BOP's
check there), #474's `Fillet002` `E4` at 2, `Fillet003`'s `E49` and `E52`
(a vertex of five edges, two of them leaving it along one line on one
face: a cusp in the input), #962's `E6` (above, upstream's).

| Case | What it covers |
|------|----------------|
| `issue273_handle_foot_e{11,15}_r{0.3,0.8,2}` | the piece of the rim from the vertex to the line's end, the cut 0.003 off it |
| `issue474_f002_sliver_top_r{0.3,0.8}` | the cut edge's ends on the fillet's two faces, one each |

## A corner's point a turn round a circle (realthunder/FreeCAD#962, 2026-10-19)

#962's arm leaves the curved wall (a cylinder of 19.75 about z) at an
upright edge where the outline turns into the body by 18.6 deg. The two
edges along the floor there -- the arm's side's foot (`E25`, a line) and
the wall's (`E26`, an arc) -- each fillet alone; together, at 0.3 and 1,
the result was invalid, 21233 for 11583 at 0.3 and 21776 for 11570 at 1
(the same at the arm's top,
`E33`/`E34`, and on the `Chamfer` input's two). Upstream's the same.

The corner of two meets the fillets' lines on the floor where they cross
(`ChFi3d_IntTraces`). The wall's line is a circle, periodic; of the
crossing's parameter on it and a period on, the one nearer the line's end
at the vertex was taken (`recadre`). The stripe is carried on past the
vertex for the corner, here by 3.4 rad of the circle, and that far end is
nearer the parameter a turn on (8.12) than the crossing's own (1.84):
the line runs 0 to 5.15, the vertex at 1.8. The fillet's edge on the
floor then ran 8.12 rad, its torus face a turn over itself.

Fix `76205151c3`: the point decides how much of the line is kept, from its far
end to there, and on a stripe that is not closed that is never more than
a turn. A parameter that would keep more is not taken where the other
keeps less; else the nearer the end, as before. A whole turn stays: on
#523's box the rim's fillet meets itself at a point, its line a whole
circle from -1.571 to 4.712, the parameter a quarter turn past the
vertex's end and the one on the line its far end (taking the one on the
line, a first try, made those two invalid). The four
results are valid and clean by BOP's check; against the input less the two
strips by booleans, mitred at the bisector of the corner, BOP's difference
both ways is empty and the volumes near the corner agree to 1e-7 at 0.3,
2e-6 at 1.

The sweeps (`76205151c3` against `5fe644b95d`): the fillet vertex
sweep turns 8 invalid results valid -- `Fillet` V18:25,26 and V24:33,34,
`Chamfer` V13:15,16 and V22:31,32, at 0.3 and 1 -- and nothing else
moves; the fillet's and the chamfer's edge sweeps and the suites are the
same.

| Case | What it covers |
|------|----------------|
| `issue962_arm_corner_e25_e26_r{0.3,1}` | the arm's side's foot and the wall's, at the corner turning into the body |
| `issue962_arm_corner_e33_e34_r{0.3,1}` | the same at the arm's top |

What is left of the edge sweep's invalid results, looked at since: #474's
`Fillet002` `E4` at 2 is a coil's end standing on a block. Below the
vertex the block's corner (`E28`) carries the edge on in line, its faces
the end face's plane and the coil's inner cylinder's tangent plane: the
fillet carried on runs along `E28` and never meets it, and the end falls
back to a plate (`PerformIntersectionAtEnd`, a face's edge the fillet does
not cross), which digs into the block below the vertex -- loose at every
radius (0.003 to 0.085), not clean by BOP's check from 0.3, invalid at 2;
upstream's the same. The right end is flat, in the plane through the
vertex square to the edge, its edge over the block's two faces and the
coil's underside: a corner of a kind the builder has none of (the flat
end at a vertex takes one face beyond). Not made. The vertex sweep's
pairs on #474's coils, 14 of the 34 whose edges are each valid alone
(`Fillet` and `Fillet001` V5 and V9, `Fillet003` V1 and V5), are at such
vertices: an edge carrying another on in line, beside a tangent edge.

## A fillet whole in the other's end (realthunder/FreeCAD#474, 2026-10-20)

#474's `Fillet002`, the block's upright edge (`E11`) and the top's edge
beside it in the same face (`E23`), at their vertex `V7`: a box corner, the
three faces square, but `E23` is 0.155 long -- the top there is the sliver
of "The far end's piece of a cut edge kept". Each alone is valid; the two,
at 0.3 and 1, invalid (BOP's check: the block's side's wire crossing
itself), upstream as well. The upright's fillet alone runs 0.3 (1) along
the common face from its edge and takes `E23` whole at its end; the two
fillets' lines on that face do not meet (`ChFi3d_IsInFront` finds them
face to face, `OkinterCC` false), the corner by intersection fails, and the
plate made a corner over the short fillet's own end, which the far end's
corner made as well.

Fix `0fe893a8a6`: face to face, the lines not meeting, where one fillet's far
vertex is nearer the vertex than the other's line on the common face is to
the other's edge, the corner is refused ("a fillet whole in the other's
end"). The upright alone is made as before. The setback fallback, on as
FreeCAD has it, makes nothing of it either: refused.

The sweeps (`0fe893a8a6` against `76205151c3`): the fillet vertex sweep's
two results there, invalid, refused; nothing else moves -- the edge sweep
and the suites (fillet, draft, thickness) are the same.

| Case | What it covers |
|------|----------------|
| `issue474_f002_whole_in_end_r{0.3,1}` | the two edges: refused (invalid before) |
| `issue474_f002_upright_alone_r{0.3,1}` | the upright edge alone: made, BOP-clean, at its volume |

Looked at, not fixed: #631's `Fillet` `V11:16,23`, the vertex where the
arm rising from the base meets the block on top -- the arm's ridge (`E15`)
and the block's upright edge (`E24`) convex, the two feet (`E16`, `E23`)
concave, the two filleted ones opposite, with no face in common. A corner
of two at four sharp edges is a plate (`PerformMoreThreeCorner`); here the
plate is a B-spline of negative area (invalid at 0.3 and 1), upstream the
same. The right result is the union of the two fillets made alone (BOP's
difference with it 2e-5 at 0.3, the plate's sliver; the union valid): each
fillet's end runs past the vertex onto the other's two faces and crosses
the other's edge carried on (0.067 past the vertex at 1), the two ends
passing 0.002 to 0.006 apart, so the plate's opening is turned inside out.
Ending each stripe as alone (`PerformIntersectionAtEnd` on each, tried)
leaves four faces open: each end takes the other's edge for a sharp one and
carries it on. A corner that ends each fillet against the other is a new
kind, not made. Over the vertex sweep, such pairs -- opposite at four
sharp edges, each edge valid alone -- are 39 not clean of 327: 21
invalid (#474's coil pairs above, 10; #962's `V34` to `V39`, 8, known;
this, 2; #273's `Fillet001` `V8:9,22` at 1, made valid in the next section),
14 refused (#876, 12; #962, 2), 4 loose (#273); the plate's quality
otherwise, as under "What is left, and why" above.

#876's twelve, looked at and left: each is a box edge (90 deg, 16.4 long)
with, opposite it, a circle edge whose faces meet at 1 deg -- a fillet a few
thousandths wide, which at 0.3 is refused alone on four of them too. The
same in the comparison sweep; refused, not invalid.

## A line run onto an edge of its face, not its end (realthunder/FreeCAD#273, 2026-10-20)

#273's `Fillet001`, the cup's rim beside the handle (`E9`, in one spine
with `E3`: the rim's half from foot to foot) at 1 -- the radius of the
fillet the input already has on the rim's other half. With the handle's
corner edge (`E22`) at their vertex `V8`, invalid at 1 only (0.3 to 0.98,
1.05, 1.2 valid): the corner's plate of negative area, 45 of volume too
much taken. The rim's fillet is a torus (a kpart: cylinder, plane, circle),
cut to its faces by hatching its lines on them (`SplitKPart`). At the
handle, the top's line meets the handle's foot (`E16`); the wall's line
runs on under the handle, inside the wall, and that side is taken on to
where its own line leaves its face -- an extension kept for the corner --
and back when it leaves for a face beyond (`SearchFace`). At 0.98 the
line crosses the input fillet's end (`E6`), a face beyond: taken back. At
1 it lies on that fillet's lower edge (`E4`, the same circle at z 17): the
hatching's domain ends where the line runs onto `E4`, at its vertex `V5`
across the handle, 5.2 off and at another spine parameter. The end's
curve ran over the torus from one to the other, and the plate built on it
folded.

Fix `033a83c84b`: such an end -- the hatching's point at the beginning or
end of a segment of coincidence (`RunsOnto`) -- is taken back as well, at
either end and on either side. The rim's fillet ends at the handle, the
mirror of the input's own (`x` 2.323 against -2.323, `y` 17.913 both).

The sweeps (`033a83c84b` against `0fe893a8a6`): the fillet vertex sweep's
`V8:9,22@1` invalid to valid (8478.7475 to 8524.0432); two refused results
made, the rim with the handle's foot (`V2:3,16@1`, `V8:9,16@1`); and three
valid ones moved, the rim alone and with `E11` (`V2:3@1`, `V8:9@1`,
`V2:3,11@1`): the old torus ran 0.2 on under the handle's face, 0.07 of
volume too much, two faces fewer. The new volume is the one the radius
gives (the rim alone at 0.98 scaled by the square). The edge sweep and the
chamfer edge sweep do not move; the suites (fillet, draft, thickness) the
same. No BOP check: the input fails it itself (40 errors, its vertices at
0.7), every result with it.

| Case | What it covers |
|------|----------------|
| `issue273_f001_rim_onto_edge_e9_r1` | the rim alone: at the handle, at the volume the radius gives (0.07 deeper before) |
| `issue273_f001_rim_onto_edge_e9_e22_r1` | the rim with the handle's corner edge: valid (a plate of negative area before) |
| `issue273_f001_rim_onto_edge_e9_e16_r1` | the rim with the handle's foot: made (refused before) |

## A repair that removed under its own iterator: a crash (realthunder/FreeCAD#876, 2026-10-20)

The chamfer sweep's two crashes, the same in every run kept: #876's
`Fillet` `E87` and `Fillet001` `E125` (the same edge, a corner arc of 0.69
in the top), chamfered at 0.3. The fillet refuses that edge at every radius
and the chamfer at 0.8 and 2; at 0.3 the chamfer's data reaches the
topological build, which makes a face whose wire is not closed. Its repair
(`CorrectUnclosedWire`, `TopOpeBRepBuild_Merge.cxx`, TKBool, as upstream)
removed each edge of fewer than two vertices from the wire while iterating
over that wire: the removal frees the child the iterator stands on, and
its `Next()` read freed memory -- a jump to a garbage address in
`MakeFaces`, the process lost. No debugger here (lldb refuses a batch run
without developer mode): a signal handler printing `backtrace()` with
`dladdr()`, loaded by the script with `ctypes`, and `atos -i` on the frame
put it on the `Next()` after `BB.Remove`.

Fix `3a0593e01f`: the edges are gathered first, then removed. Both
chamfers return: made and invalid, 5 faces and no volume (FreeCAD refuses
the result). The sweeps (`3a0593e01f` against `033a83c84b`): the two
crashes invalid, nothing else moves in the fillet edge and vertex sweeps or
the chamfer edge sweep; the suites the same.

Why the chamfer was made at all: the next section (the edge is no edge).

## A periodic pcurve sampled past its first period (realthunder/FreeCAD#876, 2026-10-20)

Those chamfers' edge is no edge: #876's flat top is split along a rounded
rectangle into two coplanar faces, both facing up, and its corners are
arcs of 0.69 (`Fillet`'s `E85`, `E87`; `Fillet001`'s `E123`, `E125`, two
corners each), numbered 2 pi to 5 pi/2 and 5 pi/2 to 3 pi. `ChFi3d::IsTangentFaces` samples the two
pcurves with `LocalAnalysis_SurfaceContinuity`, which takes only
parameters within a curve's first and last -- 0 .. 2 pi for the pcurves,
full circles -- though a periodic curve is defined at any: every sample
was refused, and with none done the faces were "not tangent". The fillet
failed later (refused); the chamfer built an invalid result, or crashed
before `3a0593e01f`.

Fix `ce3b4bff39`: both pcurves periodic with one period, the samples are
shifted by whole periods into their range. The arcs are tangent, and
refused at once ("There are no suitable edges for chamfer or fillet").
The same gap in `LocalAnalysis` stands for its other callers -- sewing,
`BRepOffset_Analyse`'s own use, `GeomPlate` -- not touched.

The sweeps (`ce3b4bff39` against `3a0593e01f`): the chamfer edge sweep's
six invalid results on those arcs refused (`E85` and `E123` at 0.3 and
0.8, `E87` and `E125` at 0.3); the fillet edge and vertex sweeps do not
move; the thickness sweep (928 runs, `BRepOffset_Analyse` calls
`IsTangentFaces`) the same with and without it; the suites the same.

| Case | What it covers |
|------|----------------|
| `issue876_fillet_chamfer_flat_split_e{85,87}_r{0.3,0.8}`, `issue876_fillet001_chamfer_flat_split_e{123,125}_r{0.3,0.8}` | the chamfer on a split of a flat face: refused, the input as it was (invalid before; at 0.3 on 87 and 125 the suite died, before `3a0593e01f`) |

## An audit of the work (2026-10-21)

The fork's fillet, corner, draft and thickness changes (31 500 lines over
149 files since upstream's `b8f597c677`) were read through end to end,
the thickness chain for the first time on this box. Three commits of the
fork carry what it found, none with a case of its own -- a fault that
changes a result on an input the suites have, and hardenings of paths
they do not reach:

- `017f9991f1` (TKBool, TKTopAlgo): `BRepCheck_Analyzer` printed a bare
  line number to stderr for every invalid sub-shape; `BRepAlgo_Loop` read
  `BREPALGO_LOOP_WALK` from the environment on every face; `BRepAlgo_Image`
  handed out a plain static list; `BRepFill_Filling` left C1 and C2 at G0.
- `333ae78a2d` (TKFillet): `ChFi3d_EdgesCoverTheirEnds` moved a located
  curve's point by the edge's location a second time (a placed shape's
  tolerance fix skipped); the long-extension flag was put back by hand,
  not on every way out; a four-edge corner with no edge to extend and
  `PerformIntersectionAtEnd` called each other until the stack ran out;
  `EdgesToArc`'s walk of ten; four unchecked lookups (`Extrema`, a
  projection sequence, a pcurve, a vertex's parameters on a face without
  it); `IsTangentFaces` shifted a straddling range by one period;
  `ChFiDS_FilSpine::Law` walked past its laws.
- `6c218d2662` (TKOffset): a draft refused for a vertex at a touch came
  back Done when another draft ran in between; a refused draft kept the
  refused shape; `TrimEdge`'s skip of the edge's ends depended on the
  vertices' order; a null test of C1 made twice where one was C2.

The harnesses got the same reading: a refused case passed on any Python
error (the sub-shape lookups are outside the `try` now, and only
`Part.OCCError` is a refusal); the thickness `nocrash_case` could not fail;
its determinism cases passed on eight refusals alike; the document cases
and the thickness and BOP sweeps did not apply `loose_ends.py`, and the
BOP sweep skipped every `LOOSE` baseline result; `issue962_e56_r0.8`'s
picture carried the volume from before 2026-10-13; the thickness README
called a fixed case broken and had non-ASCII; two case lists here expanded
to names that do not exist. Suites after: fillet 678 PASS 5 XFAIL, draft
105, thickness 378.

Read and left as they are, for a case that would show them: in-place
pcurve edits of edges handed to `BRepAlgo_Loop` (harmless while every such
edge is a fresh piece), a second crossing vertex at one point, the
thickness context intersections ignoring their `ExtentContext`/`InSide`
arguments since the port, `EdgeInter`'s end-hit mode dropping interior
crossings, `ExtentFace`'s step edges in hash order, `ContextIntByArc`'s
second image, the glue of a stay face's first image only, and
`Precision::Confusion()` where a vertex's tolerance belongs in
`BRepOffset_MakeLoops`.

## The opposite corner (`e9bd6ed68f`, realthunder/FreeCAD#631, 2026-10-21)

Two fillets ending at a vertex of four edges whose faces there share
nothing -- the filleted edges opposite round the vertex, a sharp edge
between them on each side: #631's V11, #474's Fillet003 at V5, #962's
V34-V39, 21 invalid pairs of the vertex sweep. The builder took them for a
corner of two stripes and closed it with the plate (`PerformMoreThreeCorner`),
which has nothing to span: each fillet, alone, ends in a cap carried out of
the faces beyond the vertex (`PerformIntersectionAtEnd`), and the two caps
lie on each other's faces. The right result is the union of the two
fillets made alone (`opp/` of the vertex sweep: the fuse of the two, the
same to 1e-10).

`ChFi3d_Builder::PerformOppositeCorner` builds that: each stripe ended as
alone, then the DS told how the ends share the vertex. Of the four edges,
each spine's keeps its stub from the vertex to the other fillet's cap (a
vertex interference at the vertex, the spine's own side under its fillet);
each sharp edge keeps the piece from the vertex to its nearer cap -- a
concave edge between the two caps, bounding its faces from the other side,
so a curve of its own in the DS, reversed on both -- loses the piece
between its two caps, where they meet on one plane, and keeps what lies
past the farther. TopOpeBRepBuild dropped the vertex's own pave on an edge
carried on past it (`TopOpeBRepBuild_PaveSet::Prepare`, an interference
vertex at the edge's end oriented the other way); it keeps it, beside the
other, when the fillet asks (`TopOpeBRepBuild_PaveSet_PastEndPaves`, this
computation only). The ends must come out as two ends alone -- one new
point on each spine edge beyond the vertex, two on each sharp edge -- or the
corner is refused.

It is a fallback (`ComputeOppositeCorners`), never the first try: run first
on the vertex sweep's 392 opposite pairs that are not refused, it broke 61
the plate had right or loose (#631's and #962's with volumes far out) and
mended 7. So the plate runs as before, then the setback fallback where the
computation failed at a vertex, and where the result is still invalid or
missing the computation is made again with the opposite corner at every
such vertex, kept on the setback fallback's terms (valid, every fillet
made, no edge looser than the input's or a twentieth of the radius, no
fold); otherwise the computation as it was. The setback fallback goes first
because it makes some of these corners where the plate fails -- the floor
and the inline edge of a slot by a slope (`slot_by_slope_floor_inline_*`,
`issue962_floor_corner_*_floor_inline_r1`), #962's V34-V39 fillet pairs at 1
-- and, run after the opposite corner had failed, it failed on all of them
(8 suite cases and 22 vertex sweep results refused in the first build).
Mended: the miniature at every radius and #631's V11 at 0.3 and 1 (exact).
Which result the plate gives depends on the order the edges are given: the
miniature's feet with the one along y first leave the plate invalid, and the
corner is made; along x first the plate's result is valid, loose (0.028 at
1) and up to 0.09 off the union (at 3), and it stands. #962's V34-V39 stayed invalid: the pattern there was
not two ends alone (one spine's new point at the vertex itself, a sharp edge
with one contact), and the corner refused them, so the plate's result
stood -- made since (next section). So does #474's Fillet003 at V5 (edges 5 and 21, invalid at 0.3 and
1): neither fillet's cap reaches the other's spine edge -- edge 5 is a coil
82 long that comes back to the vertex's line -- and on both sharp edges the
nearer contact is the vertex itself. The debugging build of the corner
mended it (0.07 of 1983.6); the corner as committed refuses it. Taking a
spine edge with no new point as having no stub, and dropping a nearer
contact at the vertex, makes the corner build, but the result is not the
union (an edge of 0.26 at 0.3, the fillets not found in it): the checks
throw it out. Measured 2026-10-21, left as XFAIL.

| Case | What it covers |
|------|----------------|
| `roof_block_feet_r{0.3,1,2,3}` | the miniature's two feet, the one along y first: valid, the union of the two alone to 1e-6, BOP clean (invalid before at every radius) |
| `roof_block_feet_x_first_r{0.3,1,2,3}` | the same feet, the one along x first: the plate's own result, valid, edges within 0.05, within 0.1 of the union (as before) |
| `issue631_opposite_e16_e23_r{0.3,1}` | #631's V11: the union to 1e-4 (invalid before) |

## The opposite corner, ends that pass the vertex by (`224c0a90f8`, realthunder/FreeCAD#962, 2026-10-22)

#962's rail, V36 to V39 of the `Fillet` input (V34 to V37 of the `Chamfer`
input, the same rail): the edge along the top of a tooth (`E52`, `E54`) and
the edge up its slope (`E74`, `E82`, `E84`, `E92`), opposite round the
vertex. At 0.3 the plate's result is invalid (edge tolerances to 7.36), and
the opposite corner refused them. Each fillet alone ends square to its
spine, its cap in the plane of one of the other's faces, so the ends are
not quite two ends alone:

- the slope's spine edge lies in the plane of the top fillet's cap, and the
  top's spine edge meets the slope fillet's cap at the vertex only: no stub
  on either. A spine edge with no stub is now taken as gone from the vertex
  on (a vertex interference at the vertex, its own side out). Without it the
  edge has no interference, the builder takes its state from the vertex,
  where the curves of a cap are kept, and the slope's whole tangent chain
  came back as a face round the top fillet's cap;
- the sharp edge along the top under the slope gets one contact, from the
  slope fillet's line; its nearer contact is the vertex, there is no piece
  to keep, and it is gone to the contact and kept past it;
- the short sharp edge across the step gets one contact from the caps, the
  slope fillet's line ending on it; its nearer contact is the top fillet's
  own line ending on it, which FilDS puts on the edge after the corners.
  That point is now taken as the nearer contact: the piece from the vertex
  to it a curve of its own, reversed on both faces, as before, and the
  stripe's common point taken off the edge (FilDS would put it back, and the
  edge is to be gone from the vertex to the farther contact).

Two faults of the builder showed on the way. An interference put on an edge
with `DStr.ChangeShapeInterferences(anE).Append(...DStr.AddShape(anE)...)`
went nowhere when the edge was not yet in the DS: the list is taken before
the argument adds the edge (the order is the compiler's). And the first
computation's plate raised an input vertex 3.5 from V36 to 3.82 in place --
the result shares the input's vertices -- and the corner's computation,
made after on the same input, kept it. The input's vertex and edge
tolerances are now taken when the computation starts and put back by
`Reset()` before each computation a fallback makes.

The sweeps (against `e9bd6ed68f`): the vertex sweep's 8 results there,
invalid, are the union of the two alone (11583.6228, 11697.3152), tolerance
1e-4; nothing else moves in either sweep; the suites are the same; the
thickness sweep 928 of 928. At 1 the plate's results are valid, 0.63 off the
union, and stand; V37 at 1 is refused as before. #474's Fillet003 at V5 is
not mended by it.

| Case | What it covers |
|------|----------------|
| `issue962_opposite_v{36,37,38,39}_e*_r0.3` | #962's rail: the union to 1e-4 (invalid before) |

## Corners set back where the plate's result is invalid (`e352f81743`, realthunder/FreeCAD#962, #474, 2026-10-22)

#962's rail has grooves between its teeth: a floor (`F27`, z 14) between
two teeth's walls, open at x 38.5 onto the body's side (`F17`), the teeth's
slopes (`F26` and its like) overhanging the mouth. The floor's edge at the
mouth (`E54`, convex) and a wall's foot (`E90`, concave, carried on along
the wall's pieces to the groove's end, `E89` and `E88`) are each made
alone; together, at 0.3 and 1, the result was invalid -- 5.8 of volume too
much at 0.3 -- at the groove's four corners (`V36` to `V39`) and at the
`Chamfer` input's four (`V34` to `V37`). Upstream's is invalid at 0.3
and refused at 1.

The corner is one of opposite concavity at four edges: the slope stands
in, above the floor, for the outer face of the corner of three that
`PerformTwoCorner` makes (its edges with the side face and with the wall
are the two sharp edges more), so the plate made it. The floor edge's
fillet runs on past the vertex on the side face, which goes on under the
tooth: its line there ends on the side face's far edge, 10 away, and the
plate, built over that end, cut into the tooth.

The computation's result was taken as it came; the setback fallback ran
only where the computation failed. The vertices where it builds a plate
are recorded now (`PerformMoreThreeCorner`, `ChFi3d_PlateCorners`), and
where the first computation's result is built but invalid
(`BRepCheck_Analyzer`) and a fillet ends at one of them, the fallback sets
those corners back as it does where the computation fails there -- on its
own terms for a result it hands back. When it finds nothing valid it
computes the result as it was, as after a failure. It runs after the
opposite corner, which mends an opposite pair's invalid plate better (the
union of the two alone). The check costs a `BRepCheck_Analyzer` of the
result, and only where a plate was built; a chamfer is left as it was (the
fallback sets back fillets only), and so is everything with FreeCAD's
`FilletCornerSetbackFallback` at 0.

The groove's corners come out valid and clean by BOP's check, a set-back
patch between the floor edge's fillet, the wall's and the slope. The union
of the two alone is no reference here: in it the wall's fillet stands over
the floor edge's round, the floor under it a face upside down; the set-back
corner is 2e-3 under it at 0.3 and 0.06 at 1.

The sweeps (`e352f81743` against `224c0a90f8`): 60 invalid results
valid, nothing else moves. Vertex 57: the groove's 16; #474's coil pairs
at `V5` and `V9` of `Fillet` and `Fillet001` (24, clean by BOP's check;
"an edge carrying another on in line, beside a tangent edge", above); and
`Fillet003`'s corners at `V1`, `V5`, `V26`, `V27` (17), among them `V5`'s
opposite pair, which the opposite corner refuses (0.07 under the union at
0.3, the case no longer known broken). Edge 3: `Fillet003`'s `E52` at 0.3
and 0.8 (clean) and `Fillet002`'s `E4` at 2. Nine of the 60 are valid and
not clean by BOP's check, a self-intersection: `Fillet003`'s `V26:44,52`,
`V26:52,53`, `V27:46,52`, `V27:52,56` at both radii, and `Fillet002`'s
`E4` at 2 -- invalid before, the input clean. The suites: fillet 711 PASS
5 XFAIL, draft 105, thickness 378; the thickness sweep 928 of 928.

Not mended by it: #962's `E6` (its end at a ledge 0.05 wide, which faces
down: the cap the fillet needs faces up, in its plane) and the sets that
hold it, and #474 `Fillet002`'s `V2:1,5`, `V2:2,5`, `V4:4,14` -- the
fallback finds nothing valid there, and the result is the invalid one it
was, after the fallback's computations. (2026-10-25: `Fillet002`'s cases all hold `E5` or `E14`,
the coil's top-outer and bottom-inner corners, refused alone. The coil
starts on its leg's top, overlapping it, and over the leg's width of 2 the
helix rises 0.12: the coil's outer face comes out of the leg's top as a
wedge of no height at `V2`, the leg's top left as a sliver of 0.103 beside
it. The chain over the four turns is computed and only `V2` fails
(`BRepFilletAPI_MakeFillet`'s faulty vertex): a radius of 0.3 has no side
there to roll on. A one-turn coil of the same section, built without the leg,
fillets at every long edge at 0.3 and 1.)

| Case | What it covers |
|------|----------------|
| `issue962_{fillet,chamfer}_groove_v*_e*_e*_r{0.3,1}` | the groove's four corners on both inputs: valid, clean by BOP's check, the volume to 1e-3 (invalid before) |
| `issue474_coil_v5_e5_e20_r0.3`, `issue474_coil_v9_e12_e25_r1` | #474's coil with the block's upright edge carrying it on: valid, clean by BOP's check (invalid before) |
| `issue474_f003_opposite_e5_e21_r0.3` | `Fillet003`'s `V5`, made now, within 0.1 of the union (known broken before) |

## A common point on another edge (`55f74fd428`, realthunder/FreeCAD#474, 2026-10-22)

#474's `Fillet003` coil leaves a block (x -17 to -9, y -4 to 0, z 11 to
13): its outer side (`F2`, x -13 at the block) rises from the block's
front (`F7`, y 0) at an upright edge (`E6`, concave), its top runs on from
the block's top (`F3`) across an edge 1.6 deg sharp (`E2`, along x). The
block's top edge (`E10`) and the coil's foot (`E6`) are each made alone;
together the corner at `V1` (-13,0,13) was invalid at 1 -- the block's top
face a wire crossing itself, 0.73 under the union of the two alone -- and
the same at the bottom (`E21` with `E6` at `V5`). At 0.3 the first result
was invalid as well, and the setback fallback mended it (above).

Four sharp edges, two fillets on a common face: the plate makes the
corner. `E10`'s line on the block's top runs on past the vertex as far as
the face does, to its far end (x -9), and the stripe's common point there
is on that end's edge (`E8`). Where a stripe's common point lies farther
from the vertex than the sharp edge's point, the plate steps the sharp
edge back to it, by the point's parameter on its arc -- here `E8`'s,
taken on `E2`: `E2`'s point at 1.09 along it, and the stripe's end out at
x -9. The plate's edge on the fillet ran diagonally from there to the
fillet's contact with `E6`'s, 5.2 long, and the top face was pinched in
two at its corner.

A common point on another edge has no parameter on this one. Stepped back
only to points on the edge, the sharp edge's point stays at the vertex,
the stripe's end where it meets the other fillet, and the plate is a
compact corner (picture). That is not the better corner everywhere: at
#474's coil on its block's upright edge (`Fillet` and `Fillet001`, `V5`
and `V9`) both neighbours of the sharp edge are stripes, and the plate,
kept at the vertex, spans the stripes as far as they run past it -- valid,
clean, 0.46 over the union at 0.3 where the set-back patch is 0.06 under
it, several radii long. Made the old way those corners are invalid and the
setback fallback mends them; at #962's groove the plate came out creased
where the set-back patch is smooth; and at #876's `E30` and the edges like
it (one fillet at the corner) the plate is invalid where the old step
made the corner refused. So the step is corrected only as a last resort:
where the result is invalid at a corner the plate made, after the setback
fallback, the plates are made again stepped back on their sharp edges only
to points on them (`ChFi3d_PlateStepBackOnEdge`), and the result is kept
where valid by the setback fallback's measure (the tolerance bound, every
fillet made, no fold within three radii); else it is computed as it was.

The sweeps (`55f74fd428` against `e352f81743`): the two invalid results
valid (`V1:6,10` and `V5:6,21` at 1, clean by BOP's check, 0.23 and 0.10
over the union of the two alone, which keeps a step where the concave
fillet stands above the convex one's round), nothing else moves, not a
volume; the chamfer's edge sweep is the same. The suites: fillet 713 PASS
5 XFAIL, draft 105, thickness 378; the thickness sweep 928 of 928.

| Case | What it covers |
|------|----------------|
| `issue474_f003_coilfoot_v{1_e6_e10,5_e6_e21}_r1` | `Fillet003`'s coil foot with the block's top or bottom edge: valid, clean by BOP's check (invalid before) |

## A bisection that could not end (`0198e783ae`, realthunder/FreeCAD#273, 2026-10-23)

#273's `Fillet001`, edge 12 at 0.3 -- a B-spline wall's edge on the plane
at z 18 (`F2` and `F10`) -- ran 17 hours before it was stopped. Sampled,
it was in the setback fallback's corner of more than three edges, which
projects a curve on a B-spline surface (`CurveHermite`,
`ProjLib_CompProjectedCurve`). Where the projection leaves the surface,
`DichExactBound` bisects between the last parameter projected and the first
that is not until the two are `Tol` apart, and `Tol` is the surface's
tolerance over the projection's speed on it: near a singular point it can
be below the spacing of doubles at the parameter. The middle is then one
of the ends, the interval no longer shrinks, and the loop never ended. It
now stops there; the fillet is refused in 2 seconds, as it is when the
input is written out and read back.

That is why the sweep never saw it: every case fillets a copy read back
from the input's text, and written out, two planes' axes change in their
last digits -- enough that the projection never came to that point. The case reads the file as it is.

The sweeps (`0198e783ae` against `55f74fd428`): byte-identical, every case
and volume; the suites: fillet 714 PASS 5 XFAIL, draft 105, thickness 378;
the thickness sweep 928 of 928.

| Case | What it covers |
|------|----------------|
| `issue273_f001_e12_r0.3_ends` | `Fillet001`'s edge 12 at 0.3: refused in seconds (it never ended before); a hang is the failure, the summary line missing |

## The cut off the face into a round (`5847016bbd`, realthunder/FreeCAD#273, 2026-10-23)

#273's `Fillet001` is the handle of "A cut that runs off the face" after
the Fillet: the top's edges rounded at 1 -- a B-spline round (`F14`) across
its end (`E34`, y 15.30), cylinders (`F15`, `F16`) along its sides. The
pocket's rims are `E38` (the base), `E39` and `E40` (apex 22 deg at (0,
15.01, 31), 0.29 short of the end). A rim at 0.3 ends at the apex as in the
handle: its cap in the other wall runs off the top, and the cut is carried
on into the face beyond `Eob` -- the round now, not a plane. The round is
tangent to the top across `E34`, and so is the fillet across its line on
the top: the two touch where that line meets `E34` (Q). `GeomInt_IntSS`
found no line between them and the walk did not start from its middle, and
the corner was refused (the fillet's curve on `Fob` from Q to P).

Where it is not found, it is made of their points: between Q and P, each on
the plane across the chord at it, by `PointOnThree` (P's own solver: the
fillet's (u, v) such that the point lies on the round and the plane),
interpolated by chord length. Its pcurve on the fillet goes through the
points' (u, v) on the same parameters -- P lies past the fillet's bounds,
where a projection finds nothing -- and on the round it is projected. It
is kept within ten times the approximation tolerance, as the segment from P
to R is (1e-7 here). `E39` at 0.3: valid, 0.162 off, the rim's strip about
0.155 with its ends; its base corner (79 deg, the top 0.29 wide there, the
fillet's line running onto the side's round) set back.

`E40`, its mirror, is still refused, and not for this: its stripe ends
where its side on the wall meets the apex's edge (`E45`), its line on the
top 0.06 past the apex and on no edge, and the cut off the top is taken
only from a line that ends on the top's edge (`E39`'s ran on to `E34`). At
0.8 and 2 both rims are still refused, not traced.

The sweeps (`5847016bbd` against `0198e783ae`): six refused results made,
nothing else moves -- `E39@0.3` and its vertices' sets (`V23:39`,
`38,39`, `39,42`, `38,39,42`; `V25:39`). BOP's references fail on this
input (it fails BOP's check itself); each set is within 0.006 of the sum of
its single fillets' volume changes (-0.229 for -0.223, -0.128 for -0.134,
-0.190 for -0.195). The suites: fillet 715 PASS 5 XFAIL, draft 105,
thickness 378; the thickness sweep 928 of 928.

| Case | What it covers |
|------|----------------|
| `issue273_f001_apex_off_round_e39_r0.3` | `Fillet001`'s pocket rim `E39` at 0.3, its apex end cut off the top into the round: valid (refused before) |

(`E40` made since: next section.)

## The cut off the face from the line's end (`57ca3587ff`, realthunder/FreeCAD#273, 2026-10-23)

`E40`, `E39`'s mirror on `Fillet001`, at 0.3. Its stripe ends where its
side on the wall (`F21`) meets the apex's edge `E45`; its common point on
the top is then the section's other end, (-0.29, 15.07, 31), inside the top,
0.26 short of `E34`. The fillet's line on the top is a line, and its range
runs on to `E34` (the line's end 2e-15 from it): it is the line, not the
stripe, that reaches the top's end. The corner carries the line on to the
other wall's plane, which it crosses past the top -- no crossing in the
range, so not the usual cap -- and the cut off the top (above) is taken only
from a common point on an edge of the top. `E39`'s side on the top reached
`E34` before its side on the wall reached `E45`; `E40`'s did not, and it was
refused: "OneCorner : bouchon non ecrit".

Where no crossing is found and the common point lies inside `Fop`, the
line's end is looked for on an edge of `Fop` (not one of the vertex's,
between two faces, within its tolerance or ten times the approximation
tolerance): found, the common point is put there, on that edge, with the
transition a walk gives a line ending on an arc, and the cut off `Fop` is
tried from it as from `E39`'s. The point is taken back when that cut is not
made. `E40` at 0.3: valid, 8534.9958 (`E39` 8534.9956); both rims at once
8534.8383, within 0.005 of the two alone; with the base rim `E38` too,
8534.7655 (`E38` alone is still refused). At 0.8 the apex corner is now
made too, and the base corner refuses it ("Failed to find edge"); at 2 not
traced.

The sweeps (`57ca3587ff` against `5847016bbd`): five refused results made,
nothing else moves -- `E40@0.3` and its vertices' sets (`V24:40`,
`38,40`, `40,43`, `38,40,43`; `V25:40`), each within 0.0003 of its mirror
among `E39`'s (8534.9291 for 8534.9289, 8535.0295 for 8535.0294, 8534.9677
for 8534.9675). The suites: fillet 717 PASS 5 XFAIL, draft 105, thickness
378; the thickness sweep 928 of 928.

| Case | What it covers |
|------|----------------|
| `issue273_f001_apex_line_end_e40_r0.3` | `Fillet001`'s pocket rim `E40` at 0.3, its stripe ending on the apex's edge, the cut off the top from its line's end on the top's edge: valid (refused before) |
| `issue273_f001_apex_both_rims_e39_e40_r0.3` | both rims at once: valid (refused before) |

## #360: the spike made no more (`fb9200b0fd`, realthunder/FreeCAD#360, 2026-10-23)

"Fillet produces a spike in the model": the `Support` body's `Fillet008`,
four edges of the side (x -53.2) of a block standing out of the front
(`F15`, y -70.5) at 4 -- the foot `E29`, the upright `E31`, the slope
`E30`, all convex, and `E28`, concave, between the side and the front.
`E29` runs on, tangent, round `Fillet007`'s r3 and up the slope's foot to
`E28`'s lower end, where the convex chain meets the concave edge. The
stored result reaches z 51.4 on a part 10 to 30 high. No code change: the
spike is not made on the fork, and has not been since `fb9200b0fd` (a
corner plate that misses its boundary is built again at G0) -- found by
running the fillet on each picture stage's library: `6d61205cc1` and
upstream 8.0.1 make it, invalid, about 550 points of its faces out of the
part (to z -14.6), `1e6f5a464c` and on do not.

The stored input has a vertex at a tolerance of 37.2 (`E28`'s lower end:
`Pad016`'s, as the reporter's 2021 build stored it -- `Pad016` recomputed
now has 1e-7 everywhere, the same volume); BOP's check fails on that
input for it, 306 vertices. On it the fillet is valid, 85451.6916, inside
the part; on the input recomputed (`Pad016`, then `Fillet007` at 3) the
same volume, clean by BOP's check, and the three convex edges at once
equal to the boolean of their single fillets (85420.6738). With `E28` the
boolean is no reference: the corner's blend is 0.3 to 0.6 off it. The
document's full recompute was stopped at 25 minutes for memory on the 8 GB
box (../occ-issues/README.md), and is not looked into here.

`fillet_case` takes `within=True` now: the result's tessellation inside
the input's bounding box. A fillet takes material away or fills a concave
corner, and makes nothing outside; a spike does, at a volume it hardly
changes. On the stored result 2620 points are outside.

| Case | What it covers |
|------|----------------|
| `issue360_f008_four_edges_r4` | #360's four edges on the input recomputed: valid, clean by BOP's check, the volume, inside the input's box |
| `issue360_f008_convex_three_r4` | the three convex ones: the same, and equal to the boolean |
| `issue360_f008_stored_input_r4` | the four on the input as stored (a vertex at 37.2): valid, the volume, inside the box |

## The flat end where the line runs on (`2a8844e8e6`, realthunder/FreeCAD#273, 2026-10-24)

The two sections before #360 make `Fillet001`'s pocket rims with the flat
end at a vertex off (OCCT's default, and a FreeCAD Fillet's from an older
file): the cut runs out of the pocket past the apex, into the round at the
top's end. With it on (`cd24623b20`, a FreeCAD Fillet from version 1), the
fillet is to end at the apex, flat. `E39` did; `E40` did not. `MakeFlatEnd`
took the parameter of the end of the fillet's line on the top
(`Fio.Parameter`) for the stripe's common point there, but `E40`'s line,
a KPart's, runs on 0.26 past that point, to the top's end `E34` (above).
The point it classified, the line's end, was on `E34`, not inside the top,
and the flat end was refused -- the usual cap instead,
the cut 0.44 past the apex along the rim. Where the common point does not
lie at the line's parameter, it is now projected onto the line (within the
line's range, ten times the approximation tolerance), and the interference
is set to that parameter. `E40` ends at the apex: 8534.9994, `E39`
8534.9992, 0.0036 less taken than without the flat end, and nothing deeper
than 1e-3 more than 0.05 past the apex (the flat face is square to the rim,
not to the pocket's axis). The base rim `E38`, whose line runs on
past both base corners (79 deg), was refused the flat end at both and cut
0.05 past each at 0.3, 0.15 at 0.8; it now ends flat at both, nothing past
them. Both rims at the apex together are a corner of the two fillets, flat
end or not (8534.8383): it rounds over the tip, 0.05 deep to 0.13 past it,
gone by 0.27 -- with the flat end, until the next section.

The sweeps with `FLAT=1` (`2a8844e8e6` against `57ca3587ff`): only
`Fillet001` moves, all valid before and after -- `E40@0.3`, `E38@0.3`,
`E38@0.8` and the vertex sets with `E40` or `E38` at 0.3 (11 of 12242),
each with one or two faces more. The fillet suite 725 PASS 5 XFAIL, the
cases below among them. Without the flat end nothing changes: the code
runs only with it on.

| Case | What it covers |
|------|----------------|
| `issue273_f001_apex_flat_e39_r0.3` | `Fillet001`'s rim `E39` at 0.3, the flat end on: ends at the apex |
| `issue273_f001_apex_flat_e40_r0.3` | its mirror `E40`, whose line runs on past its point: ends at the apex (cut into the round before) |
| `issue273_f001_apex_flat_both_rims_e39_e40_r0.3` | both rims, the flat end on: the corner of the two, as without |
| `issue273_f001_base_flat_e38_r0.3`, `_r0.8` | the base rim `E38`: flat at both base corners (cut past them before) |

## Both rims: the tip filleted (`aeed3655f6`, realthunder/FreeCAD#273, 2026-10-24)

With the flat end at a vertex on, one rim ending at a pocket's narrow tip
ends flat; both rims at once met there as a corner of two fillets, flat
end or not, and that corner ran out past the tip into the top: on #273's
handle 0.27 at 0.3 and 0.76 at 0.8, on a clean 22 deg pocket 1.36 and
2.81, on a 60 deg one 0.55 and 1.52 (how far the cut, deeper than 1e-3,
reaches along the pocket's axis past the tip). Asked for instead (the
user, 2026-10-24): the tip's own edge -- the upright the flat end would lie
on -- filleted too, so the three fillets make the corner inside the tip,
unless the two leave no face there.

`ChFi3d_FilBuilder::ComputeWithFlatEndCorners`, which
`BRepFilletAPI_MakeFillet::Build` calls for `Compute`: with the flat end
on, at each vertex of three faces where two contours end -- on its two
convex edges, at an acute angle between them, its third edge concave and
in no contour -- that edge is added, at the radius both contours have at
that end (`ChFiDS_FilSpine::RadiusAtEnd`, the constant one or the one set
at the end's parameter, as `BRepFilletAPI_MakeFillet::Add` sets it; equal,
or nothing is added). Not done with it, the edges added are removed and it
is computed again without them, on a topological builder of its own. A
right angle or more is no narrow tip: a rectangular pocket's corner is as
before. Without the flat end nothing is added.

On `Fillet001` the three were refused, though valid: at the base corners
the setback fallback made them, and `AreFilletsMade` turned the result
down. It asks each filleted edge's middle to lie off the result's faces by
half of what a fillet moves it, r (1 / cos(a / 2) - 1): for the tip's edge,
concave at 22 deg, 1.28 at 0.3 -- but the tip filled, its middle is 0.5
from the top and the floor, the pocket being 1 deep. It now asks at most
half the radius; a fillet dropped leaves the middle on a face, still found.
That changes what it asks only where the faces meet under 60 deg or over
300.

Results, rims only, the flat end on: the tip's edge filleted, nothing cut
past the tip -- the handle 8559.5564 at 0.3, 8560.4721 at 0.8 (the same as
with the upright asked for), `Fillet001` 8535.2232 at 0.3 (at 0.8 still
refused, by its base corners, as the rims alone); the handle's base rim
with a side rim (`E22`, `E23`) meets at a base corner of 79 deg, filleted
there too, 8558.2038.

The sweeps (`aeed3655f6` against `2a8844e8e6`, the flat end off against
`57ca3587ff`): the edge sweep (3921) unchanged, off and on -- one edge
ends no two contours. The vertex sweep (12242), off: 3 EXC -> ok,
`Fillet001`'s `V25` with its upright (`E45`) and one or both rims at 0.3,
by the cap; on: those 3, and the two-rim tips `V14`, `V15`, `V16` of the
handle and `V23`, `V24` of `Fillet001` at 0.3, valid before and after,
with the tip's edge added (volume up, one or two faces more); none worse.
The fillet suite 729 PASS 5 XFAIL, the cases below among them.

| Case | What it covers |
|------|----------------|
| `issue273_pocket_flat_e23_e24_r0.3`, `_r0.8` | the handle's both rims, the flat end on: the apex's edge filleted too (the two met past it before) |
| `issue273_pocket_flat_e23_e24_e30_r0.8` | the same with the apex's edge asked for: the same |
| `issue273_pocket_flat_e22_e23_r0.8` | a base rim and a side rim, the flat end on: the base corner's edge filleted too |
| `issue273_pocket_both_rims_e23_e24_r0.8` | both rims without the flat end: as before |
| `issue273_f001_apex_flat_both_rims_e39_e40_r0.3` | `Fillet001`'s both rims: the tip's edge filleted (refused with it before, by `AreFilletsMade`) |
| `pocket_rect_corner_flat_rims_r0.3` | a rectangular pocket's corner, both rims, the flat end on: nothing added |

## The tip's edge at a smaller radius (`f5902943f4`, realthunder/FreeCAD#273, 2026-10-24)

Where the tip's edge cannot be filleted at the rims' radius, the section
above leaves the corner as the two rims make it -- and they meet far past
the tip. Filleted at r, a concave edge between faces at a fills the tip
r (1 / sin(a / 2) - 1) back along its axis: a 10 deg tip, 8 long, at 0.8
8.4, past its walls; the two alone cut 5.6 past the apex there. Probed over
V pockets 8 long (10 to 80 deg, 1 and 3 deep, 0.2 to 2.5): only such tips
failed -- 10 deg from 0.8, 22 deg 3 deep at 2.5 -- and with the edge's own
radius smaller they were all made, the corner of three inside the tip (at
10 deg 1 deep, 0.8 on the rims: the edge at 0.1 to 0.7 cut nothing past the
tip, at 0.05 0.23; at 22 deg 3 deep, 2.5: 1 and 1.5 nothing, 0.5 0.24, 2
refused). Asked for (the user, 2026-10-24): a smaller radius for the tip's
edge.

`ComputeWithFlatEndCorners` now, before removing the edges it added, tries
them again at half their radius, then a quarter, then an eighth, each from
a topological builder of its own; a corner of fillets of two radii is made
as one of one. Halving lands inside the clean range above: 0.4 at 10 deg,
1.25 at 22 deg. Only the added edges are halved, all of them at once, and
only where the computation at the full radius failed: nothing made before
changes.

Results, rims only, the flat end on, each valid and clean by BOP's check,
nothing past the tip: 10 deg 1 deep 8994.8063 at 0.8, 8995.2424 at 0.95;
10 deg 3 deep 8986.7907 at 0.8, 8982.7652 at 1.5 (the two alone failed
BOP's check there, flat end or not), 8987.7699 at 2.5; 22 deg 3 deep
8969.0308 at 2.5; 5 deg 1 deep 8996.9606 at 0.8.

The vertex sweep with the flat end on (12242, `f5902943f4` against
`aeed3655f6`): unchanged -- a first version, setting the radius in
place, crashed at the six two-rim tips at 1, where the rims themselves
fail. Without the flat end
nothing is added. The fillet suite 732 PASS 5 XFAIL, the cases below among
them.

| Case | What it covers |
|------|----------------|
| `pocket_v10_d1_flat_tip_rims_r0.8` | a 10 deg pocket's both rims, the flat end on: the tip's edge at half the radius (the two met 5.6 past the apex before) |
| `pocket_v10_d3_flat_tip_rims_r1.5` | the same 3 deep at 1.5: the tip's edge at half (the two alone failed BOP's check) |
| `pocket_v22_d3_flat_tip_rims_r2.5` | a 22 deg pocket 3 deep at 2.5: the tip's edge at half |

## A face's B-spline bounds at the fillet's end (`2bde18d4b5`, realthunder/FreeCAD#631, 2026-10-24)

#631: "Fillet at a loft edge joint gives a wrong but valid shape (radius >
3 mm)". The document's `Loft` stands on a pad; its `Fillet` (15) takes the
joint of the two (`E18` of the loft's solid, concave, under the loft's
overhang), a line ending at two vertices of four edges: on the pad's side
and the loft's. The loft's faces are planes, as a loft between two
rectangles with parallel sides makes them, but each a B-spline of 2 x 2
poles. Filleted, the joint's volume over the loft's went with the radius
as r squared times 0.523 at 1, 0.509 at 3, then 0.572 at 4, 0.719 at 10,
0.904 at 15; the loft rebuilt with its faces planes gives 0.529 to 0.526,
as a straight edge between planes does. At the end at x = 4.02 a face of
the fillet's own came out, 5.3 at 4, 128 at 15, reaching x = 8.14, past the
solid: a bulge out of the pad's side, valid, 85 over at 15 (the fillet
itself 118).

The end (`PerformIntersectionAtEnd`, a vertex of four edges) cuts the
fillet on each face it crosses, between the points found on the edges
there. On the loft's side the cut lies past the side's bottom edge, outside
the B-spline's parameter range (u -10 to 0, the cut from -10 to -10.09 at 1,
to -11.42 at 15); `ChFi3d_BoundFac` keeps the box within those bounds, the
intersection found nothing, and the end was given to the plate
(`PerformMoreThreeCorner`). A plane has no bounds: the same cut on it is
found. Now a B-spline or Bezier face, not periodic, whose cut's ends lie
outside its bounds is extended first (`ChFi3d_ExtendSurface`, as the end's
other branches extend a face), the cut made on the extension, and the face
takes the extended surface, as it would a plane's.

Results, the joint at 0.3 to 20: the volume the planes' loft gives, to
1e-4, 15 faces, valid and clean by BOP's check at every radius; the
document's `Fillet` 9919.5607 (10004.5590 before). The edge and vertex
sweeps, flat end off and on, the edge sweep at 4 and 10, and the chamfer's
edge sweep: nothing moved.

| Case | What it covers |
|------|----------------|
| `issue631_loft_joint_e18_r{1,4,10,15}` | #631's loft joint: the volume of the loft rebuilt with plane faces, to 1e-3 (a bulge out of the pad's side from 4 before), clean by BOP's check |

## An invalid result refused (`6271a7f719`, 2026-10-25)

`ChFi3d_Builder::Compute` gave back whatever it, or the last of its
fallbacks, had made: the caller got `IsDone` with a shape BRepCheck rejects,
and `makeFillet` returned it. FreeCAD's features check the result and fail,
but the fallbacks that come after (the long extension) never had their
chance, and a direct caller of the API had to check for itself. Now a result
BRepCheck finds invalid is no result: the computation not done, the shape
kept for `BadShape()`, `HasResult()` true. The check runs before the long
extension, which then gets to try, and again after it, should it give the
invalid result back as it was.

Measured against `2bde18d4b5`, every move is an invalid result, and no
sweep has one left:

| Sweep | Invalid -> refused | Invalid -> valid |
|-------|--------------------|------------------|
| edge, flat end off and on | 7 | 0 |
| vertex, flat end off and on | 30 | 0 |
| edge at 4 and 10 | 19 | 2 |
| chamfer edge | 115 | 0 |

The two made: #474 `Fillet003`'s E2 and E18 at 10, invalid with tolerances
of 0.097 and 0.055, now made by the long extension at 0.007 and 0.002. Of the suite's XFAIL cases two that
were invalid are refused now: `issue962_rib_chamfer_1.2` and
`boss_corner_foot_r1`, which its row below calls refused -- it was invalid
at `2bde18d4b5`. The
time added is a BRepCheck of each result made: the suite took 214 s with
it, 233 s at `2bde18d4b5`.

| Case | What it covers |
|------|----------------|
| `issue962_invalid_refused_e6_r{0.3,0.8}`, `issue273_invalid_refused_e38_r2`, `issue876_invalid_refused_e100_r0.8_chamfer` | invalid results before, refused now, the input left as it was |
| `issue474_f003_invalid_long_extension_e{2,18}_r10` | invalid before, made by the long extension now, clean by BOP's check |

## Sliver faces taken out, in FreeCAD (`4e3ee3d5c7`; fcad `3292264f25`, `967a0656f0`, realthunder/FreeCAD#962, 2026-10-25)

#962's E6, the ring's cone edge at the gap's end face, refused at 0.3, 0.8
and 2 since `6271a7f719` (invalid before): the fillet's end runs past a
ledge 0.05 wide at z -7, a step between the cone (down to r 16.7) and the
bore below it (r 16.75). Ending there would take a face facing up beside the
ledge facing down, which no end of the builder makes. The ledge is no
modeling intent: two features meant to meet. Of the sweeps' shapes only
three have a face under 0.1 wide, and each sits at one of the sweeps'
remaining failures: #962's ledge; #474 `Fillet002`'s face of the coil's
leg, 0.05 wide, where the coil comes out of the leg's top with no height;
#474 `Fillet003`'s face of no area at its cusp.

The rule lives in FreeCAD, which decides to change a user's model, not in
the kernel: where a PartDesign Fillet or Chamfer fails on some edges, the
faces at those edges narrower than a quarter of the radius (twice the area
over the perimeter) are taken out with upstream's `BRepAlgoAPI_Defeaturing`
(`TopoShape::makESliverFree`), the edges found again through its history,
and the dress-up built again; kept only when fewer edges fail. The removal
itself is kept only when every sliver went, the shape passes BRepCheck and
BOP's check, and its volume moved no more than the slivers' width times
their area. On #962: the cone runs on to the bore (r 16.75 at z -7.05, 0.108
of volume more), and E6 is made at 0.3, 0.8 and 2, E9 at 0.3 and 0.8, valid
and clean by BOP's check. #474 `Fillet002`'s sliver cannot be taken out
(defeaturing leaves the shape as it was), and `Fillet003`'s leaves a shape
BOP's check finds dirty: both stay refused.

A refusal of an invalid result names no faulty contour, which FreeCAD's
partial build (`makEFillet`) took for success: it now builds each edge
alone to find the ones that fail, as its chamfer does. And building again
after such a refusal gave the input back, done: `Reset()` leaves the builder
of the result (`myCoup`) with the pieces of the computation before; each
`Compute` now starts with a fresh one, as the fallbacks did
(`4e3ee3d5c7`; the suite and the sweeps unchanged).

`models/pictures/issue962_sliver_removed_e6.png`: the input and FreeCAD's
Fillet at 0.3 and 0.8 (not made by `make_pictures.sh`: the kernel alone
refuses it). FreeCAD's `PartDesignTests.TestFillet.TestFilletSlivers` covers
it on a block with a 0.05 step.

## Features past which a fillet runs, in FreeCAD (fcad `0559e4b1b2`, `386a9ab57b`, realthunder/FreeCAD#273, 2026-10-25)

#273's E20, the top's side edge beside the triangular pocket in the top, is
made up to 1.2 and refused from about 1.26: the fillet's line on the top
lies r from E20 and reaches the pocket's corner, and past it the fillet
would run over the pocket's rim -- a fillet over another feature's edge,
which the builder does not make (the refusals' table below). Modeled by
hand, the pocket comes after the fillet and cuts into it. That order is
what FreeCAD now tries: where a PartDesign Fillet or Chamfer still fails on
some edges after RemoveSlivers, the features near them are taken out
(`TopoShape::makEFeatureFree`), the dress-up built again, and the features
put back -- the material a pocket took cut from the result, a boss's fused
to it. Kept only when fewer edges fail and the result is valid and clean,
with as many solids as before (property `PastFeatures`, on by default).

A feature is a set of faces joined by edges, grown from a face within the
radius of a failed edge (a bounding box test first, the exact distance
after), bounded by the faces that hold a failed edge or touch one of its
vertices -- those stay. One with more than 12 faces, a face beyond four
radii, or a face that, with the faces beside it, is not a plane, cylinder,
cone, sphere or torus is not taken: on B-splines `BRepAlgoAPI_Defeaturing`
ran over two minutes (#273 `Fillet001` E26 at 2, 137 s; 0.1 s now, still
refused). Each feature is taken out alone first and kept when the shape left
is clean; those kept are taken out together. The edges are found again
through the removal's history, an edge split by it as the piece through its
middle.

Clean here is BRepCheck on the whole shape and BOP's check only on the faces
the removal made (`Part::RegionBooleanCheck`), each step given 3 seconds at
most: BOP's check of all of #273 `Fillet001` took 170 s. RemoveSlivers uses
the same check and the same limit to elementary surfaces now.

On #273 `Fillet` E20, by the feature: 1.2 is made directly (8550.3805, the
fallback not used); 1.5, 2 and 2.5 are made past the pocket, 8545.2476,
8534.1852 and 8520.1466, each valid and clean by BOP's check, in about half
a second; with `PastFeatures` off each fails as before. #962's E6 and E9 are
as with RemoveSlivers alone (E6 at 0.3, 0.8 and 2; E9 at 2 still refused).
FreeCAD's `PartDesignTests.TestFillet.TestFilletPastFeatures` covers a pocket
and a boss beside a filleted edge, each against the fillet made first and
the feature cut or fused after.

`models/pictures/issue273_past_pocket_e20.png`: the input and FreeCAD's
Fillet at 1.5, 2 and 2.5 (not made by `make_pictures.sh`: the kernel alone
refuses it).

Over the edge sweep's 1321 refusals at 0.3, 0.8 and 2, a PartDesign Fillet
with both fallbacks on (2026-10-25, the whole run 159 s, no case over 4.7
s; before the limits to elementary faces cases ran 88 to 103 s):
339 are edges between two faces smooth across them (coplanar pieces of one
wall), which the kernel refuses ("no suitable edges") and FreeCAD leaves as
they are; 591 are edges FreeCAD does not take (tangent, not C0), 197 at each
radius; 7 are made, valid and clean by BOP's check -- #273 E20 and E21 at 2
(one line; the pocket), #962 E6 at 0.3, 0.8 and 2 and E9 at 0.3 and 0.8 (one
ring; the ledge). The 384 left fail in the builder: 58 at 0.3 (#273
`Fillet001` 9, #474 `Fillet002` 12 and `Fillet003` 11, #876 `Fillet` and
`Fillet001` 12 each, #962 `Fillet` 2), 67 at 0.8 and 259 at 2.

The 58 at 0.3, by cause, none new: #273 `Fillet001`'s are at its face F3,
a B-spline 0.3 wide whose edges' tolerance is 0.71, over the radius (not a
sliver by the rule; defeatured by hand it runs 89 s and changes nothing);
#474's are the coil's leg (above, "The sweeps' last refusals"); #962's E2
and E3 are the 0.05 ledge's own edges (E2 made at 0.1); #876's are its
post. There the foot (89 deg, `E30` to `E32`, `E91` to `E94`) and a ring of
1 deg creases (`E42`, `E53` on the plate's corner cylinder where the
drafted corner stands flush with it; `E56`, `E60`, `E64`, `E68` where the
plate's walls run on as the post's drafted ones) meet: `E91` and `E42` are
two pieces of one arc of radius 3, so a chain from either runs on into the
other, its angle jumping from 89 deg to 1 at the vertex. A crease of 1 deg
alone is made at 0.3, 2 and 10 (and of 0.5 deg), so it is that vertex, the
flush post's corner, again.

The 259 at 2 (2026-10-25): 63 are edges refused at a smaller radius too.
Of the 196 refused only at 2, each was measured -- the largest radius made
(bisection from 0.8, to 0.04), the fillet's width on each face (r tan of
half the angle between the faces' normals) and the room there (the distance
from the edge to the face's other edges that touch neither of its ends):

| Edges | Why |
|-------|-----|
| 120 | A face beside the edge narrower than the fillet: made up to within 10% of the room (5% over it at most) |
| 38 | A face exactly as wide as the fillet at 2 (room 2.000): made to 1.96 -- the fillet as wide as its face, as `issue273_pocket_wall_wide_e23_r1` (XFAIL) |
| 15 | Made past one face's room, refused at the other's or at a face exactly 2 wide (#876's 1.414 corners at 1.96, #962 E67 to E69 and E128 at 1.48 against a 1.5 face, #273 `Fillet001` E38 at 0.99 against a 1.0 face, #474 `Fillet002` E11 on the coil at 1.44) |
| 2 + 1 + 1 | Known: the D-hole (#273 E38, `Fillet001` E55, 1.36), the band 2 thick (#474 `Fillet003` E52), the ledge (#962 E9) |
| 4 | #962 E26 and E34 (and the `Chamfer` input's E16, E32): the ring's outer rim from the gap's end face to where the arm leaves it, made up to 1.025. Plane and cylinder only, with room 3 and 6: **a builder failure**, reproduced on a ring (radii 19.75 and 16.75, 6 high) with an arm whose side leaves the rim at (17.356, -9.425) and a gap whose end face, through the axis, meets the rim at (-13.616, -14.306): the arm's side leaving the rim 10 deg off its tangent refuses the rim at every radius, 18.6 deg (the input's) from 1.05, 5, 30 or 45 deg makes it at 0.5 to 2; with the gap alone or the arm alone it is made. Made with the flat end since `117c549667` (below, "A fillet whose line misses the face at its end") |
| 4 | #273 `Fillet001` E11, E22, E30, E33: made up to 1.29, the four meeting at the corner (4.98, -15.55, 30.04) on the handle's B-splines. Looked at (2026-10-26): room enough on every face (10.4 and 32.2 beside `E11`, 8.6 and 30.8 beside `E30`, against a fillet 1.59 and 0.97 wide at 2); from 1.35 the walk along `E11` on the handle's B-spline face comes back twisted on it (`BlendFunc_ConstRad::TwistOnS1`, the point on the face going back against the spine), at 2 on both faces near the foot, the last SurfData, so nothing to mend it from ("adjustment by reprocessing the non-written points: no neighbor"). The handle face curves gently there (radius 16.3 to 16.8 along `E11`); whether the twist is the surface's or its parameters' is open |
| 6 | Refused at exactly 2, room 3 on both faces at the edge -- each a limit of the shape (looked at 2026-10-26): #876's E6, E14 (`Fillet001` E36, E42) are not hole rims but the bottom edges of the plate's ends, arcs of radius 5.25; their chain runs on round the plate's whole bottom outline, and the post is hollow from below, its cavity 2 in from the flush sides (the bottom face's inner wire, 2.000 from the outline at (-17, -16.75)): there the bottom face is exactly as wide as the fillet at 2 (the walk fails from that corner; made to 1.99), as in the row above. #523's E11, E13 are the top rims of a 270 deg boss of radius 2: a fillet of 2 leaves nothing of the top inside its line (made to 1.99) |
| 5 | #474 `Fillet003` E3, E8, E16, E32, E40: the coil band's end, made up to 1.74 where the band is 1.992 thick -- on the coil whose input is faulty |

## The sweeps' last refusals at 0.3, 0.8 and 2: each a limit of the shape (2026-10-25)

Since `6271a7f719` no sweep has an invalid result. The edges the edge sweep
refuses at its own radii that it made invalid before, looked at one by one
with the library before it (`2bde18d4b5`), radius by radius:

| Edge | Valid up to | Why no fillet past it |
|------|-------------|-----------------------|
| #273 `Fillet` E38, `Fillet001` E55 | 1.39 (invalid from 1.41) | The ceiling's arc of a blind D-shaped hole (a cylinder of radius 3.15, a flat at x = -1.75, the ceiling at z = 16). The fillet's line on the ceiling is a circle of radius 3.15 - r: past 1.4 it misses the flat altogether, and the fillet cannot end there -- it would run on round the flat side, the flat's ceiling edge (E42) with it. Before the refusal, a torus out through the flat |
| #273 `Fillet` E20 | 1.2 (invalid from 1.3) | The top's side edge beside the triangular pocket in the top: the fillet's line on the top lies r from E20, and the pocket's corner (1.52, 7.12) about 1.26 from it. Past that the fillet runs into the pocket's rim -- a fillet over another feature's edge, which the builder does not make. Made by FreeCAD at 1.5, 2 and 2.5, the pocket taken out and cut back (above, "Features past which a fillet runs") |
| #474 `Fillet003` E52 | 1.99 (invalid from 2) | The coil's leg goes down through the coil's band and ends flush with its underside: E52 is where the leg's bottom (F28, its 2 x 4 section) meets the band's underside, 4 deg off flush. The band is 2 thick, and the fillet fails from exactly that radius |
| #474 `Fillet003` E49 | none: invalid at every radius, 0.1 too | A defect of the input, at the leg's corner: over the band's thickness (z 27.66 to 29.66) the leg's side F23 is a slit -- the band touches the leg across it, solid on both sides (sampled at z 28.66; above the band only the leg's side is solid) -- and the corner line holds two coincident edges there, E49 (F23, F26) and E47 (F23, the band's end face F21, in F26's plane). The lower 2 of E49 is no corner, and the fillet cut into the slit. A refine, a fuse with itself, a cut and fuse at the band's top all leave the slit as it is |
| #962 `Fillet` E6 (and E9) | refused at 0.3, 0.8, 2 | Its end past a ledge 0.05 wide: made by FreeCAD, which takes the ledge out (above, "Sliver faces taken out") |

The vertex sweep's refusals of the same kind are corners holding such edges:
#474 `Fillet002`'s at the coil that comes out of its leg with no height;
`Fillet003`'s V27 and V28 at E49, and V25 at E42 -- the band's top on the
leg's side (F23, the face E49 bounds too), refused alone at every radius
before and since. At V25 the input has a face of no area (F22, 1e-6),
bounded by two coincident edges up the leg's corner (E45, E48) and one of no
length -- the band's end against the leg's other corner, as the slit is at
E49's; #962's at the gap. What is left to do in the kernel here is the
fillet that runs over another feature's edge (E20), a capability of its own
-- made in FreeCAD for now by taking the feature out and putting it back;
#474's junction of coil and leg is two defects of the input that no healing
tried removes.

`models/pictures/issue474_refusals.png` shows #474's: the leg in the band
with E52, E42, E49 and F22 marked, E52 at 1.99 and at 2, and `Fillet002`'s
coil leaving its leg (made by hand from the GUI's renders, not by
`make_pictures.sh`).

## A fillet whose line misses the face at its end (`117c549667`, realthunder/FreeCAD#962, 2026-10-25)

Found sorting the edge sweep's refusals at 2 (above): #962's ring, its
outer rim at the floor (`E26`, and `E34` at the top) from the gap's end
face to where an arm leaves the rim, is made up to 1.025 and refused from
1.05, plane and cylinder only, with room 3 and 6 on its faces. At the
arm's end the floor runs on under the arm (the end is OnSame), and the
fillet's end is the cap in the arm's side, carried back. That side leaves
the rim 18.6 deg off its tangent, so carried back it passes the ring's axis
at R cos 18.6 deg = 18.72, and the fillet's line on the floor, a circle of
radius R - r, meets it only while r < R (1 - cos 18.6 deg) = 1.03. Past it
the line meets that plane nowhere: `IntersUpdateOnSame` finds nothing, and
"OneCorner : bouchon non ecrit". A ring of the same radii with the side at
10 deg is refused from 0.30 (0.5 on), at 30 and 45 deg made to 2; with the
arm alone or the gap alone, made -- the D-hole's limit (#273's E38, above)
is the same kind of end.

No cap can be made there, so the fork's flat end (`MakeFlatEnd`, used
where FreeCAD asks for it, as its new Fillet features do) takes it too:
where Fo's line, a line or a conic, carried on whole meets the face at end
nowhere, the fillet ends square to the rim at the vertex, the flat face
between the section, the rim's vertical edge (`E48`) up to the fillet and
the line in to the fillet's line on the floor. But only as the last resort:
the corner marks the end it found no cap at (`ChFi3d_UncappedEnd`) and
fails as before, and only where everything after it fails as well -- the
builder's own fallbacks, the corner edges `ComputeWithFlatEndCorners` adds
-- is the whole computed once more with such ends made flat
(`ChFi3d_MissedFlatEnd`). Taken at once, the end took #273's D-hole too:
the rim of its flat at the bottom (`E36`), whose line on the bottom face
passes the hole's cylinder (3.75 from the axis, the cylinder 3.15), and
whose fillet the corner setback fallback (above), the end set back from
the vertex, takes round into the cylinder -- a smooth end where the flat one leaves a step (Fillet.md has
pictures). Two things the pocket's tip,
the flat end's first use, never met: the fillet's point on the floor at
that end is not yet the line's (the line runs on 340 deg round, past the
gap), so the crossing of the line and the flat plane nearest the vertex is
taken, not the one nearest that point; and the section, a torus cut by a
plane through its axis, ran the long way round the tube (three quarters of
a circle, a face of area -232), so it is computed on the fillet's surface
about its two ends only. Both only where the new case applies.

On the ring at 18.6 deg the fillet is now made at 1.05, 1.5, 2 and 2.9, at
10 deg at 0.5, 1 and 2, valid and clean by BOP's check; the volume taken is
the section's area, r^2 (1 - pi/4), swept along the rim at its centroid's
radius (30.39 at 2: 0.858 x 19.30 x 1.834). On #962 `E26` and `E34` are made
at 1.5, 2 and 2.5 (11553.7502 at 2), valid and clean. Without the flat end
all of them are refused as before. The sweeps are unchanged without the
flat end; with it, only #962's `E26` and `E34` (and the same rim in
`issue962_Chamfer`, `E16` and `E32`) go from refused to made. Cases
`ring_arm_*`, `issue962_ring_rim_flat_e{26,34}_r2`, and
`issue273_dhole_rim_flat_e36_r2` (the D-hole still taken round).

## A fillet whose line runs off its face short of the vertex (`5ab71bc3ea`, realthunder/FreeCAD#876, 2026-10-26)

The last of the sweep's refusals at 0.3 sorted above: #876's post, its
foot (`E30` to `E32`, `E91` to `E94`, 89 deg) refused at 0.3 and 0.8. The
plate's long sides are flush with the post's, and the plate's corner arcs
are the post's (radius 3) from the long side to 41.6 deg, where the plate's
rim leaves the post, tangent to the arc. The plate's top narrows to
nothing at that vertex, between the foot and the rim, and the fillet's
line on the top, r out from the foot, meets the rim short of it -- 24.6
deg of the arc short at 0.3 (where 3 / (3 + r) is the cosine). Past that
there is no top to carry the fillet. The face at end, the plate's side
carried up, is tangent to the post's corner at its foot: with the post
drafted (#876's, 1 deg) the post leans away from it and the line on the
post never meets it ("OneCorner : cap not written", the vertex of four
sharp edges with the 1 deg crease between the post's corner and the
plate's, `PerformIntersectionAtEnd`); with the post straight the plate's
side carried up is the post's own wall, met by the line only tangent to
it, and the corner, whose walk stopped at the rim, went to the plate
(`CurveHermite`). A model of it, a post 40 x 33.5 with corners of radius 3
on a plate whose rim runs on tangent from 45 deg, refused the same, drafted
or not, at 0.3 and 1.

With the flat end at a vertex (`MakeRimFlatEnd`) the fillet ends flat in
its section, square to the spine, through the point where its line meets
the rim: the flat face lies between the section, the line on the top from
the foot out to the rim, and the line up the post to the fillet's line on
it. The foot is kept sharp from there to the vertex, and the top's strip
between the foot and the rim with it. As the ring's flat end (above), only
the last resort: such an end is marked as the corner meets it, and only
where everything else failed is the whole computed once more with such
ends flat (`ChFi3d_MissedFlatEnd`), the other ends as they were. Marked
whether or not the corner there fails: on #876's foot it throws at one end
and is made at the other, its mirror image, and on the drafted model it is
made at both, and the result refused each time. Not where the face beyond
the edge has no width: #474's `Fillet003` has a needle at the top of its
edge 51, a plane of no area between two edges on one line, and its fillets
that end there (`E1`, `E15`, `E31`, `E39`) would cut the one edge, its
piece kept lying on the other: made so, BOP's check found them
self-intersecting. Refused as before.

The top then touches itself at the point on the rim: the strip kept beside
the foot and the top beyond the fillet's line meet there and only there.
The builder made them one face whose wire passes that vertex twice, which
BRepCheck lets be and BOP's check calls unorientable. The fork's split of a
face that is two regions touching at a point (#523, above), which took a
wire through two coincident vertices, now takes one through a single vertex
twice as well: a face for each loop of the wire, the face's other wires
(#876's bolt hole in the top) to the piece they lie in, and that run again
until no face is pinched (a fillet made flat so at both its ends on one
face). Not where a loop is no longer than ten times what the vertex covers,
as the coincident vertices' rule has it: #273's handle at 0.8 has a fillet
face whose wire passes a vertex of tolerance 0.011 twice with a loop of one
edge 3.2e-4 long between, and cut off, it made a face of no area. Unlike
the flat end, the split applies to every result; the sweeps below say what
it changes.

With the flat end (the run-on below has taken its place on these models)
the volumes were those of the section swept along the foot from one flat
end to the other: r^2 (1 - pi/4) at its centroid, r (10 - 3
pi) / (3 (4 - pi)) out from the foot, over 45 deg - acos(3 / (3 + r)) of
each corner arc and the 27.5 between -- 0.57328 at 0.3 and 5.98824 at 1,
the result's to the last digit; drafted, the faces at 91 deg, within 2e-4
of the same estimate. On #876 the foot along x=20 is made at 0.3
(+0.54425) and 0.8 (+3.68648), along x=-20 at 0.3, valid and clean by BOP's
check; without the flat end refused as before. At 2 the line on the top
meets the rim before the corner's arc begins, on the straight foot, and
the end was not this one: refused then (made since, "Past the corner's
start" below).

The sweeps without the flat end are unchanged, the edge and vertex sweeps,
the edge sweep at 4 and 10 and the chamfer's. With it, only #876's post's
foot goes from refused to made: on `issue876_Fillet` `E30` to `E32` and
`E91`, `E93`, `E94` at 0.3 and 0.8, and their vertices (`V27`, `V28` and
the two at the other end, 64 cases at 0.3 and 1), valid and clean by BOP's
check; on `issue876_Fillet001`, the next fillet's input, the same foot
(`E99` to `E101`, `E107`, `E110`, `E111`, 64 vertex cases), valid, BOP's
check reporting only the input's own five edges off their faces. Taken
first without the needle's guard, the split's loop length, and with the
end's SurfData of no face dropped as the corner looked at it: #474's
`Fillet003` was made self-intersecting at the needle, #273's handle at 0.8
gained a face of no area and lost another case's fault for a different
one, and #474's `E22`, made at vertex 15 before, came out another way.
None of that now.

| Case | What it covers |
|------|----------------|
| `post_flush_on_plate_flat_r{0.3,1}` | the post straight: run on to the vertices (below), the volume the booleans' |
| `post_flush_draft_on_plate_flat_r{0.3,1}` | the post drafted 1 deg: run on to the vertices (below), the volume the booleans' |
| `post_flush_on_plate_r0.3_refused`, `post_flush_draft_on_plate_r0.3_refused` | without the flat end, refused as before |
| `issue876_post_foot_flat_e91_r{0.3,0.8}`, `issue876_post_foot_flat_e30_r0.3` | #876's post's foot, made, run on to the vertices (below) |
| `issue876_post_foot_e91_r0.3_refused` | without the flat end, refused |

### Run on to the vertex (`4316324037`, 2026-10-26)

The flat end left the foot sharp from the rim to the vertex and a step in
the fillet there; what is wanted is the fillet run on to the vertex, cut by
the plate's side carried up, the side rising in a curved triangle to meet
it. The walk already goes on past the rim: where a side's line runs off its
face at a stripe's end, the builder walks on on that face's tangent plane
to the spine's end (`ChFi3d_BuildPlane`), a SurfData of no face on that
side (the surplus the corner skips), or the same walk kept in the end's
SurfData, its line on the top ending at the rim and the other running on
(#876's foot along `E91`). `MakeRimRunOn` cuts that surface by the plate's
side surface from the point on the rim to Q, where the cut reaches the
plane through the vertex square to the spine, and ends it there. The
plate's side carried up is a face of its own, between the rim's piece from
the point to the vertex, the cut and the line up from the vertex in that
plane; the post, drafted, leans off it there, by 1 deg, and a sliver in
the end plane (the vertex, Q and the post's line there) closes the rest --
0.17 high at 1, the section's drop 0.017 out from the post. The foot is
filleted to the vertex and nothing of it kept. Each new face takes its way
in the solid from its surface's: the fillet's as the SurfData, the side's
as the plate's side.

Where the plate's side touches the post along the line up from the vertex
(the post straight), the plate's side is tangent to the fillet where the
fillet's line on the post crosses the end plane, at a saddle of the
corner's torus: the cut runs into that point along one of its asymptotic
directions, at an angle to the line, and ends there, the line up from the
vertex the edge between the post and the side carried up, no sliver
(`5c11250d99`). There the corner's fillet is the exact torus, which stops at
the section through the point on the rim with no walk past it; the torus,
its line on the post and that line's pcurves, circles and lines, are
carried on to the end plane. Any end the run-on cannot make still ends
flat (above).

The plate's side and its rise to the fillet are two faces of one plane
across the rim's piece; the run-on records that edge and the result has
the two made one, nothing else (`ShapeUpgrade_UnifySameDomain` with every
other edge kept; `5c11250d99`), as the booleans' `removeSplitter` has them.

On the models the volume is that of booleans that build the same thing --
the fillet's material on a plate wide all round, kept within the plate's
footprint and between the vertices' end planes: straight, 0.60169 at 0.3
and 6.51373 at 1 against 6.51374; drafted, 0.57822 at 0.3 against 0.57804
and 6.26522 at 1 against 6.26532; valid and clean by BOP's check, the same
faces as the booleans' (21 straight). On #876 the foot along x=20 is made
at 0.3 (+0.57175, 0.01375 more than flat at each end) and 0.8 (+3.98586),
along x=-20 at 0.3 and 0.8, valid and clean.

The flat sweeps change only in #876's foot: the same 24 edge and 128
vertex cases made, now run on; on `issue876_Fillet001` BOP's check still
reports only the input's own five edges. The sweeps without the flat end
do not reach it.

### Past the corner's start (`840f4a2b71`, 2026-10-26)

At 2 the fillet's line on the top meets the rim before the corner's arc
begins, on the straight foot: the end is the fillet along the straight
foot, on the post's flat wall, and the rim end was not taken (the walk's
faces those of the edge at the vertex). Now it is, the top bounded by the
rim and the edge at the vertex being enough. The walk past the rim on the
top's tangent plane stopped where the post's line reached the end of its
flat wall, the guide still running on round the corner: in the last resort
it goes on, the top's side kept on the plane from where it stopped and the
post's on to its corner (`ChFi3d_Builder_2.cxx`), up to the spine's end,
not the guide's, which runs on past it. The run-on takes the pieces one
after the other, each with its line on its own face of the post, its piece
of the cut, and between two pieces the section where they meet, the
surfaces' bound there across the walk (cut by a plane of its own, the
section lay off the next piece by the walk's approximation). Its other
curves take a margin over the deviation as sampled: BOP's check finds the
greatest, past the samples.

The plate's side and its rise are now made one face by hand -- the one's
wire with the rim's piece replaced by the other's edges, which take their
curves on the one's surface -- not by `ShapeUpgrade_UnifySameDomain`, which
also lowered the tolerance of edges it kept: the drafted model at 2 came
out valid but not clean by BOP's check, and 1.5e-4 off the booleans.

On the drafted model at 2 the volume is the booleans' within 1.8e-4
(24.48174 against 24.48192), valid and clean; on #876 the foot is made at 2
along x=20 (`E91`, 8689.9417) and x=-20 (`E30`), valid and clean, refused
before. The straight model at 2 is still refused: there the walk past the
rim at the far end is not kept, the post's corner one face with the
plate's side below it, and keeping it unmade #876 at 0.8.

The flat sweeps change only in #876's foot at 2: on `issue876_Fillet`
`E30` to `E32` and on `issue876_Fillet001` `E99` to `E101`, refused before,
now made -- valid and clean, the second with BOP's check reporting only
the input's own five edges. The vertex sweeps' radii (0.3, 1) are as
before.

| Case | What it covers |
|------|----------------|
| `post_flush_draft_on_plate_flat_r2` | the drafted model at 2, run on from the straight foot round the corner, the booleans' volume |
| `issue876_post_foot_flat_e{91,30}_r2` | #876's foot at 2, made |
| `post_flush_on_plate_flat_r2_refused` | the straight model at 2, refused with the flat end on |

## Known broken (XFAIL)

| Case | Symptom |
|------|---------|
| `issue962_rib_chamfer_1.2` | "Self-intersecting wire" on the rib's wall: the chain turns from the rib's top down its front on an arc of radius 1, and a chamfer of 1 or more turns back on itself there. Inherent, measured 2026-10-10: split and refined shapes alike are valid at 0.9, 0.95, 0.99 (equal volumes), refused at 1, and invalid from 1.01 to 1.5 (refused since `6271a7f719`) -- upstream's behaviour on a wall in one face. Left as it is (decided): FreeCAD rejects an invalid result; refusing early would move every chamfer along a tight arc. Refused before, at the foot, which is made now |
| `boss_flush_chamfer_r1` | The flush boss's foot chamfered: refused ("TopOpeBRepDS_DataStructure::Point"). The chamfer's cone is not tangent to the side where the boss touches it, so the cut by the side reaches the chamfer's line on the boss tangent to it -- a corner of no angle on the chamfer's face; made the fillet's way, the result was invalid. See "A boss flush with the plate's side" |
| `boss_rim_seam_foot_r1` | The boss against a round plate's rim, the rim's seam through the tangent point: refused, as before. The two cuts meet across the seam, which would have to be carried up to their point; with the seam elsewhere it is made (`boss_rim_foot_r*`) |
| `boss_corner_foot_r1` | A boss flush with two sides at the plate's corner: refused before any corner is made ("BRep_API: command not done"), as before |
| `issue273_pocket_wall_wide_e23_r1` | A fillet as wide as its face: #273's pocket is 1 deep, so at r 1 the fillet's line on the wall is the floor's edge and the fillet would take the whole wall. Refused ("StartSol echec"), with the flat end or without; up to 0.999 it is made and clean by BOP's check, from 0.9999 the wall left is a strip narrower than the input's 0.03 tolerance and BOP's check flags it, above 1 refusing is right (the line would lie below the floor). Tried 2026-10-19 and left (decided): a start rolling on the top and the floor's edge (the obstacle mode, `BRepBlend_SurfRstLineBuilder`) walks the whole rim from 1.001, but the stripe then stands on the floor's corner vertices, a cap upstream never wrote ("OneCorner : bouchon non ecrit"), at exactly 1 the lost-contact test (`BRepBlend_SurfRstConstRad::Decroch`) is a tie, and the wall would have to vanish from the result -- several sessions, no promise |

## Pictures

`models/pictures/<case>.png` shows, for each case a fix turned from failing
to passing, three results side by side -- upstream's `TKFillet` files at
`91be8c4c71`, with the files of other toolkits a fix changed
(`UPSTREAM_EXTRA` in `pictures/cases.py`), the fork just before the fix, the
fork now --
each whole and zoomed on the fillet's end. `models/Fillet.md` walks
through them. `pictures/make_pictures.sh` makes them again, on Linux or
macOS; add a case to `pictures/cases.py`, with its stage, to picture it.
(`91be8c4c71` is not the fork's base, as this section said until
2026-10-13: the branch stands on upstream 8.0.1, `b8f597c677`, 60 commits
later. Two of those touch TKFillet -- `9825547d15`, the solid's
reconstruction made reentrant, and `cffb2852ba`, crashes in StartSol --
and the pictures' first column is without them.)

## Layout

```
tests/fork/fillet/
  README.md          this file
  run_tests.py       the suite (FreeCADCmd script)
  models/            captured models and shapes
    Fillet.md        the fixes, before and after, in pictures
    pictures/        before and after, one PNG per fixed case
  pictures/          the tools that make them (make_pictures.sh)
  sweep/             every edge and vertex of the issues' shapes, against a
                     baseline (README.md there)
```
