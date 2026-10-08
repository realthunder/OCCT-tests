# Draft regression suite

Cases for the fork's fixes to drafts -- `BRepOffsetAPI_DraftAngle`, the
`Draft` package in `TKOffset`, which FreeCAD's PartDesign Draft calls.

## Running

```
FreeCADCmd tests/fork/draft/run_tests.py
```

Exit code 0 when no expected-pass case fails. The drafts go through a
PartDesign Draft feature on a `Part::Feature` base, as a user's do: Part has
no draft of its own. A case expects either a valid solid (with its volume
when known) or a refusal: the feature fails with an error, and no invalid
shape comes back.

The suite sets each Draft's `Method` to `Classic` when the FreeCAD running it
has that property (realthunder/FreeCAD `OcctFix`, 2026-10-04): its default,
`Auto`, falls back to FreeCAD's new draft when the classic one refuses, and
the cases here are about the kernel's draft itself. FreeCAD's `TestDraft`
covers `Auto`. The `new_*` cases at the end (next section) are the
exception: they run the new draft, and are skipped by a FreeCAD without it.

## Pictures

`models/Draft.md` shows each fix in pictures -- upstream, the fork before
the fix and the fork after, side by side (`models/pictures/`, made by
`pictures/make_pictures.sh`).

## A drafted face whose corner a third face touches (realthunder/FreeCAD#334, 2026-10-03)

The model (`../occ-issues/models/issue334_draft_artifact.FCStd`) drafts
ledges at 85.5 deg about the walls behind them, and from Draft001 on its
side face was broken. The document's own recompute stops at Sketch006 (its
support remapped to a curved face, a FreeCAD element-map problem), so each
Draft is recomputed alone from its base feature's stored shape. Draft and
Draft002 come out as stored; Draft001 and Draft003 come out invalid, a
"Self-intersecting wire" on a narrow slanted face (F29 of Draft001's
result, 0.9 wide).

The ledge's front corner, (18, 7.2, 63.7) in Draft001, is a vertex of four
faces: the ledge, the wall above it, the wall below it, and that slanted
face -- a bevel along the wall's top beside the ledge, which touches the
ledge at the corner only. `Draft_Modification` is a geometry-only
modification (`BRepTools_Modifier`): it gives each face a new surface, each
edge a new curve and each vertex a new point, and keeps the topology. The
corner's new point is where the drafted ledge meets the two walls,
(18, 7.2, 37.017) at 85.5 deg -- and the bevel, which the draft does not
reach, keeps its plane: two of its edges now run 8.25 off it. The true
result needs a new edge there (the wall below keeps its piece under the
bevel), which a modification cannot make. Any angle moves the corner off
the bevel: 5 deg is as invalid as 85.5.

The stored Draft001 is "valid" only because the build that saved it gave
that corner a vertex tolerance of 27.8, swallowing the error; its faces are
the same, two edges 8.25 off the bevel. Not a regression.

Fix `ca766a8a92`: once every vertex has its new point, `Draft_Modification::
Perform` checks it against the surface of every face of the shape at the
vertex -- its new surface if the draft changes it, its own otherwise --
and stops with `Draft_VertexRecomputation` on the vertex when a face
misses the point by more than 100 times the vertex's tolerance (good
vertices sit within 1e-14 of their faces; this one 8.25). The draft is
refused, and PartDesign reports it, instead of handing on an invalid body.

| Case | What it covers |
|------|----------------|
| `notch_ledge_a{5,20,45}` | a block with a notch, its ledge drafted about the notch's back wall: valid, 125 tan(a) added |
| `notch_bevel_ledge_a{5,20,45}` | the same with the block's front top edge right of the notch bevelled, the bevel touching the ledge at its corner: refused (was invalid) |
| `issue334_draft`, `issue334_draft002` | #334's Draft and Draft002 recomputed alone: valid, their stored volumes |
| `issue334_draft001`, `issue334_draft003` | #334's Draft001 and Draft003: refused (were invalid) |
| `issue474_ramp_ledge_a{11,15,17}` | #474 Fillet003's input, the ledge top drafted about its end wall after a first recompute: refused (was a segmentation fault) |

Checked with a draft sweep: every planar face of 29 shapes (the fillet
sweep's 25 and #334's four Draft inputs) against each planar face beside it
as the neutral plane, the pull direction its normal, at 5, 15 and 60 deg --
8982 drafts, each run in a process of its own. 554 invalid results and 29
crashes become refusals, and so do 2 "valid" results (#876's inputs, F47
and F33 at 5 deg) that took 40% of the solid away and held vertex
tolerances of 1.3e154. Nothing else changes: the 3510 valid results are
the same to the last digit. 893 invalid results are left, of other causes,
and one crash (#474's Fillet003 input, face 3 against face 10 at 15 deg),
both before the fix and after -- open. FreeCAD's `TestPartApp` (139) and
`TestPartDesignApp` (77, its `TestDraft` among them) pass, and the
thickness suite (326) with them.

## A ledge lifted off a helical ramp (#474's Fillet003 input, 2026-10-04)

`../fillet/models/issue474_fillet003_base.brep` has a flat ledge top, face
3 (z=13, x from -17 to -9), that meets a helical ramp, face 1 -- a radial
segment from r=9 to r=13 turning once about Z while it rises 5 -- along the
ramp's first line. Drafted about the ledge's end wall x=-17 (face 10), the
ledge tilts up toward the ramp and its far end rises 8 tan(a). At 15 deg
that is z=15.1, where the ramp is 1.5 rad round the axis: the drafted plane
no longer meets the ramp anywhere near the edge they shared, and no draft
by moving geometry exists.

`Draft_Modification::Perform` took the only branch of the plane-ramp
intersection, 9 units away, as the edge's new curve; the corner's new
point lay past its end. `SmartParameter` then extends the edge's pcurve on
the plane to the point and projects it onto the ramp to rebuild the curve.
The extension does not lie on the ramp, the approximation built nothing,
the edge was left with a null curve, and the next line dereferenced it:
FreeCAD died. In FreeCAD it shows when a Draft is recomputed in its base's
frame -- every recompute after the first, so as soon as the angle is
changed to anything from 11 to 17 deg.

Fix: `SmartParameter` says when the rebuild fails (no pcurve, no projected
piece, no approximated curve) and leaves the edge as it was; `Perform` stops
with `Draft_VertexRecomputation` on the vertex, and PartDesign reports the
draft as failed. Where `Choose` uses it only for a tangent, a failure falls
back to the parameter at the original curve's end. An approximation short
of its tolerance (`IsDone()` false with curves) is still taken, as before.

The suite's case recomputes the Draft once at 1 deg, then 11, 15 and 17:
the brep's shape carries a location, a quarter turn about X, that the
`Part::Feature` takes as its placement, and the first recompute, in the
global frame, rounds the problem differently and misses the failure.

Fix `f9d329a663`. The draft sweep (8982 drafts) turns that crash and three
exceptions -- the same ledge's face 3 against face 7, and face 7 against
face 3, at 15 deg, in #474's Fillet, Fillet001 and Fillet003 inputs; the
sweep's driver turns an access violation into an exception -- into
refusals, and changes nothing else (3510 valid, 893 invalid, the same).
The draft suite (13), the thickness suite (326), `TestPartApp` (139) and
`TestPartDesignApp` (78) pass.

## The sweep's invalid drafts (2026-10-04)

The draft sweep above left 893 drafts that came back as invalid solids --
PartDesign's Draft does not check, so a user got each of them as a body.
Sorted by what `BRepCheck` reports:

| Count | Report | What it was |
|------:|--------|-------------|
| 663 (521 at 60 deg) | a self-intersecting wire | a drafted face swept past an edge of a face beside it -- a slot's wall through the block's outer wall -- so a face the draft never touches gets a wire crossing itself; narrow walls do it at 5 deg |
| 134 | a vertex off an edge's curve, nothing else | a wall split in coplanar pieces (two solids fused, not refined) whose split edge ends at the drafted corner -- the corner moves, the split edge does not -- and, at #962, a hair's miss: 3.4e-7 on a 1e-7 tolerance |
| 41 | intersecting wires | an inner wire of a face run into its outer one |
| 27 | bad orientation of a face in the shell | a face turned inside out, nearly all at 60 deg |
| 28 | wires not closed, unorientable faces | |

A draft (`Draft_Modification`, a `BRepTools_Modifier`) gives each face a
new surface, each edge a new curve and each vertex a new point, and keeps
the topology. Most of these need a new or a vanished edge, which it cannot
make: they are refused now. The hair's misses get the tolerance that covers
them. Four changes:

- `Draft_Modification::Perform`: once every vertex has its new point, it is
  checked against the curve of each edge the draft leaves alone (as it was
  already against each face's surface). A wall split in coplanar pieces
  keeps its split edge, and a corner that slides off it is refused with
  `Draft_VertexRecomputation` -- 100 times the vertex's tolerance, as for
  the faces.
- `Draft_Modification::Perform`: an edge the draft shrinks to a point (its
  three-point chord under `Precision::Confusion()`, from over 10 times that)
  is refused with `Draft_EdgeRecomputation`, as one that turns round was
  already. One coplanar piece of a wall drafted about a plane through the
  split edge loses its top and bottom edges and its area; and a ledge
  drafted until its edge reaches the face above leaves a zero-length edge
  (valid in memory, invalid once written and read back).
- `Draft_Modification::NewPoint`: the vertex's new tolerance covers its
  distance to each of its edges' curves at its new parameters (0.1% over),
  up to the 100 times its tolerance `Perform` accepts. The point is
  computed on one edge's curve and one face's surface, and the other edges
  pass it by a hair.
- `BRepOffsetAPI_DraftAngle::Build`: every face the draft rebuilt is
  checked with `BRepCheck_Analyzer`; one that was valid in the input and is
  not in the result makes the draft not done. This catches the faces whose
  wires a drafted face sweeps across, which no per-vertex or per-edge test
  sees. `Status()` stays `Draft_NoError` for these (the error belongs to
  the modification); `IsDone()` is false. An input face already invalid is
  not held against the draft. It costs nothing measurable (a 1.2 s draft of
  #334's 179-face part, the same).

| Case | What it covers |
|------|----------------|
| `notch_ledge_a44`, `notch_ledge_a45` | the notch's ledge just short of the block's top (valid, 125 tan(a) added) and at it: refused (a zero-length edge; the suite had 45 as valid) |
| `slot_wall_a5`, `slot_wall_a{15,30}` | a slot's wall 2 from the block's front, drafted about the slot's floor: valid at 5 deg (2 * 18^2 tan(a) taken), refused past 6.3 deg where it breaks through (were invalid) |
| `split_floor_corner_a5` | a front wall drafted about the end wall, its corner where the floor's split edge and a slanted wall meet: refused (was invalid) |
| `slot_wall_split_piece_a{5,15}` | one coplanar piece of a slot's wall drafted about the side through its split edge: refused (was "invalid" at the input's volume, the piece flattened) |
| `issue962_f41_n24_a5`, `issue962_f44_n30_a5`, `issue962_f51_n30_a15` | #962's Pocket002, walls drafted about chamfer planes: valid (were invalid, a vertex 3.4e-7 off a split edge) |

The draft sweep (8982 drafts): of the 893 invalid results, 854 are refused
and 39 come out valid -- 37 within a vertex tolerance of 1e-5, the other two
#334 Draft002/003 inputs carrying the 27.8 tolerance their stored shapes
already have. No invalid result is left. The 3510 valid results are the
same to the last digit (now 3549), and no refusal, exception or crash
changes otherwise.

## The new draft (FreeCAD's `Part::CellDraft`, 2026-10-05)

realthunder/FreeCAD `docs/NewDraft.md`: a draft that can change topology,
in FreeCAD's Part, behind PartDesign's `Method = New` (and `Auto`'s
fallback). The space around the drafted face is split by the solid, the
face's new plane and its neighbours' surfaces extended, in one general
fuse, and the cells are chosen. The cases the classic draft refuses above
come out valid, each at a closed-form volume:

| Case | What it covers |
|------|----------------|
| `new_notch_ledge_a{5,20,44,45}` | the ledge: `1750 + 125 tan(a)`; at 45 the notch's front edge goes |
| `new_notch_ledge_a60`, `_unstopped` | past the top (8.66 over 5): stopped at the top's plane by default (`StopAtBody`), a fin 3.66 over the top without |
| `new_notch_bevel_ledge_a{5,20,45}`, `_unstopped` | the corner the bevel touches gets its new edge; stopped, the ledge rises only to the bevel's plane |
| `new_slot_wall_a{5,15,30}` | the slot's wall breaks through the front at `2 / tan(a)` |
| `new_split_floor_corner_a5` | the corner slides along the slanted wall, across the floor's split |
| `new_l_face_a{5,20}`, `_reversed` | an L-shaped face, both ways: `1500 -+ 625 tan(a)` |
| `new_boss_walls_a{5,30}_{xy,yx}` | two adjacent walls of a boss in either order: the same solid, the classic draft's |
| `new_issue474_ramp_ledge_a{5,11,15,17}` | #474's ledge: the ramp, extended, meets the lifted ledge; the wedge `128 tan(a)` |
| `new_face_vanishes`, `new_face_shrinks` | a 0.2 wide face whose walls meet 0.2 past it, about a plane 50 below: drafted outward it would vanish (refused, `FaceVanishes`); inward, `386.6083` |
| `new_chain_rbox_a{5,-5,-15}`, `new_chain_rbox_fillet_a5` | tangent chains (2026-10-07): a 20 x 10 x 10 block with its vertical edges filleted 2, one wall (or a fillet) drafted about the floor: the walls and fillets all round drafted, the fillets turned into cones; the section at height z a rounded rectangle with its walls in by `z tan(a)` |
| `new_chain_rbox_a{15,20}` | the same inward: the cones reach their apex at `2 / tan(a)` (7.46 at 15 deg), under the top, and above it the walls meet in a ridge (2026-10-08; refused before) |
| `new_chain_rbox_a30` | at 30 deg the short walls narrow to nothing at `5 / tan(30)` = 8.66, under the top (refused, `FaceVanishes`) |
| `new_nopropagate_rbox_{wall,all}_{new,auto}_a5` | `TangentPropagation` off (2026-10-08): only the picked faces are drafted. One wall picked: the fillets beside it are taken off and made again at radius 2 on the edges where the drafted wall meets the side walls (docs/NewDraft.md section 17). Every wall and fillet picked: the chain itself, the volume of `new_chain_rbox_a5` |
| `new_chain_open_apex_a15`, `new_chain_open_apex_fillet_a15` | one vertical edge filleted: an open chain (a wall, the fillet, the wall beyond) drafted from the wall and from the fillet, past the apex |
| `new_chain_sharp_a{5,-5,15}`, `new_chain_sharp_corner_wall_a15` | the block with the vertical edge at the origin left sharp: the chain closes there, the two new planes meeting in a new edge; from the far wall and from a wall at the sharp corner (the classic draft refuses at 15 deg) |
| `new_chain_pocket_break_a{5,10,20}` | a pocket with rounded corners 2 behind a block's front, its walls drafted outward all round: through the front wall from 7.3 deg (the classic draft refuses); the block less a ruled loft of the floor's and the top's outlines |
| `new_chain_pocket_apex_a15`, `new_chain_pocket_sharp_a15` | the pocket's walls drafted inward at 15 deg: its concave corners close 7.46 over the floor and the walls meet past it; and with its corner at (10, 2) sharp |

## Known open

| Case | Symptom |
|------|---------|
| a draft that needs a new edge | refused by the classic draft: a geometry-only modification cannot make it (a split wall, a face swept past a neighbour's edge). FreeCAD's new draft makes these (previous section) |
