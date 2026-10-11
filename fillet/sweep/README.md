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

`baseline/` is OCCT LinkVibe-801 `6c4e2bc29f`, FreeCAD OcctFix `493032cbaf`,
2026-10-12: edge 2519 ok, 32 BAD, 1370 EXC; vertex 9190 ok, 221 BAD, 2831
EXC; no crash or timeout. Move it forward with each fix that changes
results, saying in the commit what moved. The earlier ones, at `b207bd4103`
(edge 2425 / 62 / 1434, vertex 8843 / 295 / 3104), `9c44789bbb` (edge
2445 / 42 / 1434, vertex 8847 / 291 / 3104), `7a1fbeffb3` (edge 2507 /
42 / 1372, vertex 9089 / 291 / 2862), `8704591b60` (edge 2509 / 40 /
1372, vertex 9089 / 291 / 2862), `fff5d20907` (edge 2509 / 40 / 1372,
vertex 9109 / 291 / 2842) and `f7464716c0` (edge 2519 / 32 / 1370, vertex
9118 / 290 / 2834), are in this file's history.

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
and 86 valid there, invalid only in pieces. 69 of the 86 are fixed
(../README.md, 2026-10-12); the 17 left, of the 221 at `6c4e2bc29f`:

| Shape | Vertices (cases) |
|-------|------------------|
| `issue962_Fillet` | V48, V49 (6 each: the pocket mouth's edge with its neighbours, its fillet's line along the split of the block's side -- two or three fillets at the pocket's corner, one on the far piece); V2 (2: two fillets on the two pieces of a wall, one edge a circle) |
| `issue309_shape` | V8 (2: a vertex of four sharp edges) |
| `mini_finwall` | V11 (1: two fillets on the two pieces of a wall, one of them walked) |

    grep " BAD" baseline/vertex.txt > /tmp/bad.lst
    SHAPE=issue962_Fillet LIST=/tmp/bad.lst FreeCADCmd triage.py

"Valid" on the refined shape is BRepCheck's; two of the 86 fail Part's
`check(True)` there (`ok(bop)`). #474's `Fillet002` E2 was such a case
on the edge sweep: a spike BRepCheck passed.

A purged or misnamed input reads `MISSING` and its cases are not run: check
that both runs have every shape before reading "all the same".
