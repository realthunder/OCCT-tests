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
(valid, the same volume).

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
| `seam_end_top_r*`, `seam_end_bottom_r*` | the fillet on the box edge ending on the seam, top and bottom, radius 0.5 and 1 (and 2 on top) |
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
| `issue876_corner4_r{0.3,1}` | XFAIL, an exception: the process survives to the suite's summary (the build before `76a730386a` dies here, exit 139) |

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
| `arm_on_tall_block_whole_r{0.1,0.3,0.5,2}` | the corner with the block's side one face: valid (no volume: the change is below GProp's precision on the whole shape) |
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
the cylinder; see "Past the cylinder's radius", below).

| Case | What it covers |
|------|----------------|
| `mirror_top_r2` | the edge across the diagonal at radius 2: valid, the seam case's volume |
| `mirror_bottom_r2` | XFAIL, as `seam_end_bottom_r2` |

The every-edge sweep moves those two results and nothing else (3919 the
same to the last digit); the vertex sweep (12722 fillets, radii 0.3 and 1)
moves nothing. FreeCAD's `TestPartApp` (139) and `TestPartDesignApp` (77)
pass.

## Past the cylinder's radius (realthunder/FreeCAD#523, 2026-10-05)

#523's box and cylinder, the four box edges ending at the cylinder (the
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
| `seam_end_top_r{2.5,3}`, `mirror_top_r{2.5,3}` | XFAIL, refused; the boolean's volume when they pass |

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

#631's Fillet002 input: a chain of six edges round a slanted arm, ending
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

## Known broken (XFAIL)

| Case | Symptom |
|------|---------|
| `seam_end_bottom_r2`, `mirror_bottom_r2` | "Self-intersecting wire" on the cylinder, where the tops, built the same, pass: the corner's curve meets the face's circle at fourth order and an approximation within 2e-9 of the true curve crosses it (see "An end point a rounding error past the line", above) |
| `seam_end_top_r{2.5,3}`, `mirror_top_r{2.5,3}` | refused, "bouchon non ecrit": the end needs a cut over two faces across a sharp edge and splits the top (see "Past the cylinder's radius", above) |
| `issue876_corner4_r{0.3,1}` | `Standard_ProgramError`, point 0 of the DS: `ChFi3d_FilDS` stores a stripe end with no point, after the corner (-17,16.75,3) has failed (its projected curve pieces not running end to end) |

## Pictures

`models/pictures/<case>.png` shows, for each case a fix turned from failing
to passing, three results side by side -- upstream's `TKFillet` files at the
fork's base (`91be8c4c71`), with the files of other toolkits a fix changed
(`UPSTREAM_EXTRA` in `pictures/cases.py`), the fork just before the fix, the
fork now --
each whole and zoomed on the fillet's end. `models/Fillet.md` walks
through them. `pictures/make_pictures.sh` makes them again, on Linux or
macOS; add a case to `pictures/cases.py`, with its stage, to picture it.

## Layout

```
tests/fork/fillet/
  README.md          this file
  run_tests.py       the suite (FreeCADCmd script)
  models/            captured models and shapes
    Fillet.md        the fixes, before and after, in pictures
    pictures/        before and after, one PNG per fixed case
  pictures/          the tools that make them (make_pictures.sh)
```
