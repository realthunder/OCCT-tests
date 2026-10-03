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

## Known open

| Case | Symptom |
|------|---------|
| the sweep's 893 invalid drafts | other causes, not looked at yet |
