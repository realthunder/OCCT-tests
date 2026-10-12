# The fillet sweep

Every edge and every vertex of the fillet issues' shapes, filleted, against a
baseline. Run it before and after any change to TKFillet; what is not meant
to move must come out the same.

| Mode | Cases | What |
|------|------:|------|
| `edge` | 3921 | every edge between two faces, alone, at r = 0.3, 0.8, 2 |
| `vertex` | 12242 | at every vertex of 3 or more such edges: all of them, every pair, each alone, at r = 0.3, 1 |

`shapes.lst` names the 25 inputs: the draft sweep's shapes
(`../../draft/sweep/shapes`, the features' base shapes from
`../../occ-issues/models` and a few minimal ones) without #334's, and two of
the fillet sweep's own in `shapes/` -- `issue273_Fillet001` (the base of
Fillet001 in `issue273_heater_handle_fillet.FCStd`) and `issue876_Fillet001`
(the base of Fillet001 in `issue876_fillet_pocket_flip.FCStd`), both the
shapes stored in the documents.

    ./drive.py edge /tmp/f_edge                     # ~4 min on the mac
    ./compare.py baseline/edge.txt /tmp/f_edge
    ./drive.py vertex /tmp/f_vertex                 # ~19 min
    ./compare.py baseline/vertex.txt /tmp/f_vertex
    TKF=/path/to/libdir ./drive.py edge /tmp/f_new  # a rebuilt TKFillet

`drive.py <edge|vertex> <outdir> [shape ...]`, env `FCBUILD`, `RUN`, `RADII`,
`TKF` (a directory of OCCT libraries loaded first -- a rebuilt TKFillet tried
without installing it; macOS strips `DYLD_*` from a bash script's children,
so it is set inside `RUN`). One FreeCADCmd per shape (`fsw.py`), one at a
time (8 GB box). A case with no output for 120 s is `TIMEOUT`, one whose
process died `CRASH`; the rest of the shape goes on in a new process.

A case is `E<edge>@<r>` or `V<vertex>:<edge>,...@<r>` (indices as
`Part.read` numbers them); a result is `ok:<volume>:<max tol>:<faces>`,
`BAD:...` (made but `isValid()` false), `EXC` or `NULL`. Each case fillets a
fresh copy of the input: a fillet that succeeds raises the tolerances of the
sub-shapes it shares with its input, and one that fails can leave the input
changed, so reusing one input makes a result depend on the cases run before
it (the old scratch sweeps did, and their tolerances drifted along a shape).

`compare.py <before> <after>` takes an outdir or a baseline file (lines
`shape case result`): status changes in full, and among results valid in
both the ones whose volume or face count moved and whose tolerance more than
doubled or halved (`SHOW=n` of each).

`baseline/` is OCCT LinkVibe-801 `2bc692bfc4`, FreeCAD OcctFix `493032cbaf`,
2026-10-13: edge 2567 ok, 32 BAD, 1322 EXC; vertex 9463 ok, 200 BAD, 2579
EXC; no crash or timeout. Move it forward with each fix that changes
results, saying in the commit what moved. The earlier ones, at `b207bd4103`
(edge 2425 / 62 / 1434, vertex 8843 / 295 / 3104), `9c44789bbb` (edge
2445 / 42 / 1434, vertex 8847 / 291 / 3104), `7a1fbeffb3` (edge 2507 /
42 / 1372, vertex 9089 / 291 / 2862), `8704591b60` (edge 2509 / 40 /
1372, vertex 9089 / 291 / 2862), `fff5d20907` (edge 2509 / 40 / 1372,
vertex 9109 / 291 / 2842), `f7464716c0` (edge 2519 / 32 / 1370, vertex
9118 / 290 / 2834), `6c4e2bc29f` (edge 2519 / 32 / 1370, vertex 9190 /
221 / 2831), `3f7ddd4bcc` (edge the same, vertex 9204 / 209 / 2829),
`97f346ff4a` (edge 2519 / 32 / 1370, vertex 9227 / 192 / 2823),
`faf4f72ee0` (edge 2555 / 32 / 1334, vertex 9370 / 193 / 2679),
`3ba0c94072` (edge 2563 / 32 / 1326, vertex 9378 / 205 / 2659),
`726d9533c6` (edge the same, vertex 9386 / 201 / 2655), `f446ee4591`
(edge the same, vertex 9411 / 201 / 2630) and `2ff60f1efd` (edge the
same, vertex 9435 / 200 / 2607), are in this file's history.

The invalid results, each tried again on the shape refined
(`removeSplitter`, the edge found again by its middle): the edge sweep's
32 are invalid there too -- #273's `Fillet` E11, E15 (every radius), E20
and E38 at 2, `Fillet001` E16 and E55 at 2; #309's E9; #474's `Fillet002`
E4 at 2 and E11, `Fillet003` E2, E18, E49, E52, E56; #962's `Fillet` E6
-- upstream's behaviour on that geometry, not the pieces'. The eight that
were invalid only in pieces are fixed (../README.md, 2026-10-11).

The vertex sweep's 290 at `f7464716c0` (`triage.py`): 181 invalid on the
refined shape as well -- #273 (36), #309 (14), #474 (93), #631 (2), #962
(36); 23 with an edge that is a split itself, gone from the refined shape;
and 86 valid there, invalid only in pieces. 83 of the 86 are fixed
(../README.md, 2026-10-12); the 3 left, of the 192 at `97f346ff4a`:

| Shape | Vertices (cases) |
|-------|------------------|
| `issue309_shape` | V8 (2: edges 8 and 9 at a vertex of four sharp edges. The result on the refined shape passes BRepCheck and fails `check(True)`, like edge 9 alone, which is invalid on both: upstream's rather than the pieces') |
| `mini_finwall` | V11 (1: two fillets on the two pieces of a wall, one of them walked; ../README.md, Known broken) |

The 23 with a split among their edges are the sweep's "all the edges of
the vertex" where a split ends there: the builder leaves the split out, and
the fillet is that of the vertex's other edges, which the refined shape
has. 15 were invalid only in pieces after all -- three fillets at such a
vertex -- and are fixed; the 8 left hold #309's edge 9, invalid on the
refined shape as well. `triage.py` took them for `noedge` then; it fillets
the refined shape on the edges it has now, and says how many were splits.

    grep " BAD" baseline/vertex.txt > /tmp/bad.lst
    SHAPE=issue962_Fillet LIST=/tmp/bad.lst FreeCADCmd triage.py

"Valid" on the refined shape is BRepCheck's; two of the 86 fail Part's
`check(True)` there (`ok(bop)`), #309's two above. #474's `Fillet002` E2
was such a case on the edge sweep: a spike BRepCheck passed.

The refused results the same way (`grep " EXC"` for the list), at
`97f346ff4a`. Edge, 1370: 1045 refused on the refined shape as well, 261
on an edge that is a split itself (`noedge`), 14 invalid there, and 50
refused only in pieces -- 26 edges, on #962's two inputs and the
miniatures. 36 of the 50 are made at `faf4f72ee0` and 8 more at
`3ba0c94072` (../README.md, 2026-10-12); the 6 left:

| Shape | Edges (cases) |
|-------|---------------|
| `issue962_Fillet` | E1, the edge 0.05 long (3); E14 at 2 |
| `issue962_Chamfer` | E6, E21 at 2 |

Vertex, 2823: 2248 refused there too (24 of them with a split among their
edges), 248 `noedge`, 90 invalid there, and 237 refused only in pieces.
225 of the 237 are made at `2bc692bfc4`; the 12 left are on #962's two
inputs -- `Fillet` V1 and V2, its edge 0.05 long alone and with a
neighbour (6), and `Chamfer` V2 and V6, edge 6 at a distance of 1, longer
than the edge (6). All four edges at a floor's corner at 1, invalid at
`3ba0c94072`, are made at `726d9533c6`, 25 pairs at `f446ee4591`, 24 at
`2ff60f1efd` (one of them, `mini_slot_bothsplit` V13:15,18 at 1, was
made invalid in between) and 23 at `2bc692bfc4`. Eight of the refused
turned invalid at `3ba0c94072`, pairs that are invalid on the refined
shape as well (V36:52,80 and the like): 200 invalid results in all
(../README.md).

A purged or misnamed input reads `MISSING` and its cases are not run: check
that both runs have every shape before reading "all the same".
