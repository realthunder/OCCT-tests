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
`Precision::Infinite()` keeps every tangent plate, as upstream does. Only
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
the cylinder) -- open, not covered here.

| Case | What it covers |
|------|----------------|
| `mirror_top_r2` | the edge across the diagonal at radius 2: valid, the seam case's volume |
| `mirror_bottom_r2` | XFAIL, as `seam_end_bottom_r2` |

The every-edge sweep moves those two results and nothing else (3919 the
same to the last digit); the vertex sweep (12722 fillets, radii 0.3 and 1)
moves nothing. FreeCAD's `TestPartApp` (139) and `TestPartDesignApp` (77)
pass.

## Known broken (XFAIL)

| Case | Symptom |
|------|---------|
| `seam_end_bottom_r2`, `mirror_bottom_r2` | "Self-intersecting wire" on the cylinder, where the tops, built the same, pass: the corner's curve meets the face's circle at fourth order and an approximation within 2e-9 of the true curve crosses it (see "An end point a rounding error past the line", above) |
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
