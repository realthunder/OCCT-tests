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
patch changes nothing there.

Vetted 2026-10-09 on `../sweep` (edge and vertex, 16163 cases): every result
the same as without it -- volumes, face counts and tolerances included. It
is neutral there; what it fixes takes split edges at a stripe's end, which
none of the sweep's inputs has.

## chamfer-pairs-refused-2026-11-17.txt

The chamfer sweep at every vertex (`sweep/drive.py vertex`, `OP=chamfer`,
`FILLET_FIX_LEVEL=4`) at OCCT `ede9c6c5c5`: 12242 cases, 9111 made, 3131
refused. The file lists the 145 pairs of edges refused where each of the
two alone is chamfered at that size, with the number of edges at the
vertex and how many of them are sharp or smooth: 103 at a vertex of four
sharp edges (refused by rule, `3ee86acb22`), 23 at a vertex of three
sharp edges, 12 at four edges one of them smooth, 7 at five edges. Not
triaged further.
