# Work in progress, not applied

`split-edge-end-walk.diff` (against occt LinkVibe-801 `339f5add5c`):
`PerformIntersectionAtEnd`'s walk round a stripe's end when the faces there
have edges split by vertices of no other face. Two fixes:

- `cherche_edge1` took the first edge two faces share; two faces sharing two
  collinear edges (split at a vertex of theirs only) got the far one. With
  the vertex the walk passed, the one through it.
- one face met twice along a split edge was added twice, the edge "between"
  them any edge of it; now the walk goes on with the same face.

Found on #631's ramp drafted by the cell draft (fcad docs/NewDraft.md section
20), whose output had such split edges: with the patch the end at the moving
wall filleted at every radius (before: from r=8 up it failed). Not applied:
fcad now joins those edges before making the fillet again, after which the
patch changes nothing there, and it was never run on the fillet sweep
(rebuild that first: every edge and vertex of the occ-issues shapes, before
and after).
