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

`OP=chamfer` makes the same cases with `makeChamfer` at the same sizes
(2026-10-15; no baseline is kept: run it before and after a change to a
chamfer's code and compare the two).

`drive.py <edge|vertex> <outdir> [shape ...]`, env `FCBUILD`, `RUN`, `RADII`, `OP`,
`TKF` (a directory of OCCT libraries loaded first -- a rebuilt TKFillet tried
without installing it; macOS strips `DYLD_*` from a bash script's children,
so it is set inside `RUN`). One FreeCADCmd per shape (`fsw.py`), one at a
time (8 GB box). A case with no output for 120 s is `TIMEOUT`, one whose
process died `CRASH`; the rest of the shape goes on in a new process.

A case is `E<edge>@<r>` or `V<vertex>:<edge>,...@<r>` (indices as
`Part.read` numbers them); a result is `ok:<volume>:<max tol>:<faces>`,
`BAD:...` (made but `isValid()` false), `LOOSE:...:<gap>` (valid, but an
edge's curve ends past its vertex by more than ten times the edge's
tolerance -- `../../loose_ends.py`; since 2026-10-15), `EXC` or `NULL`. Each case fillets a
fresh copy of the input: a fillet that succeeds raises the tolerances of the
sub-shapes it shares with its input, and one that fails can leave the input
changed, so reusing one input makes a result depend on the cases run before
it (the old scratch sweeps did, and their tolerances drifted along a shape).

`compare.py <before> <after>` takes an outdir or a baseline file (lines
`shape case result`): status changes in full, and among results valid in
both the ones whose volume or face count moved and whose tolerance more than
doubled or halved (`SHOW=n` of each).

`baseline/` is OCCT LinkVibe-801 `6de00fea30`, FreeCAD OcctFix `34abfa2dae`,
2026-10-16: edge 2581 ok, 26 BAD, 1314 EXC; vertex 9522 ok, 6 LOOSE, 152
BAD, 2562 EXC; no crash or timeout; `1d642bfaaf` (a drafted boss flush
with the plate's side) moves no case, `b4f2f7592c` (a fillet split only
where its section is a point) only #876's at 0.3, edge 16 and vertex 112,
their tolerance 0.00524 -> 3e-4 at most, the counts the same; `892a10b753`
(a walk past a closed spine's end) moves no case, `e549e29656` (a boss's
seam through the point) two: `issue273_Fillet V5:5,6` at 0.3 and 1,
refused -> ok (vertex 9524 ok, 2560 EXC). `6de00fea30` (corner plates held to
their own miss, ../README.md) made edge 16 and vertex 112 `LOOSE` -> ok,
4 vertex refused -> valid. Before it, `a2f5c2a5d4`,
2026-10-16: edge 2565 ok, 16 LOOSE, 26 BAD, 1314 EXC; vertex 9406 ok, 118
LOOSE, 152 BAD, 2566 EXC; no crash or timeout. `a2f5c2a5d4` (a stripe
whose faces turn tangent at its end stops once both its sides are on the
face there, that last section the cut) moved only #273's `Fillet001`: 13
vertex cases at 1 invalid -> valid, and 16 at 0.3 (2 edge, 14 vertex)
without the sliver they had, 0.0002 of area, a stripe between the handle's
cylinder and itself (4e-4 less volume). Before it, `5c531f4938`,
2026-10-14: edge 2581 ok, 26 BAD, 1314 EXC; vertex 9511 ok, 165 BAD, 2566
EXC; no crash or timeout. Since 2026-10-15 (the loose-end check, no build
change) 16 of the edge results and 118 of the vertex ones are `LOOSE` in
place of `ok`: #876's `Fillet` and `Fillet001` at 0.3, 0.00262 -- a fillet
a few thousandths wide on an edge a degree from smooth, both its lines
ending in one vertex -- and 10 of #273's `Fillet` corners at 1.5e-4 to
2.6e-4; `issue273_Fillet001`'s 71 at 2.6e-4 are its input's own gap and
stay `ok`. Nothing near the 0.38 of x16win's chamfer. `8558180119` had edge 2578 / 29 / 1314, vertex
9500 / 176 / 2566 (../README.md, "BOP's check on every valid result"). Move it forward with each fix that changes
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
(edge the same, vertex 9411 / 201 / 2630), `2ff60f1efd` (edge the
same, vertex 9435 / 200 / 2607), `2bc692bfc4` (edge 2567 / 32 / 1322,
vertex 9463 / 200 / 2579), `9d58debece` (edge 2575 / 32 / 1314,
vertex 9475 / 201 / 2566), `5052552dd6` (edge the same, vertex 9476 /
200 / 2566), `afb7f305d0`, `2ec760a1d3` and `4988e007e1` (edge 2578 / 29 /
1314, vertex 9500 / 176 / 2566, the counts of today's: 20 and then 12
valid results moved, and then 6 of the edge sweep and 28 of the vertex
sweep, the edge under a wall of ../README.md) and `0669daa0b6` (the same
counts; 24 of the vertex sweep moved since) and `9735ff8875` (the same
counts, and the installed `594ece7109` gives it to the line; 4 lines of
the edge sweep and 20 of the vertex sweep changed since, 6 of those by
as much as `compare.py` prints -- the far piece's exact fillet for an
edge of a chain), are in this file's history.

The invalid results, each tried again on the shape refined
(`removeSplitter`, the edge found again by its middle): the edge sweep's
32 are invalid there too -- #273's `Fillet` E11, E15 (every radius), E20
and E38 at 2, `Fillet001` E16 and E55 at 2; #309's E9; #474's `Fillet002`
E4 at 2 and E11, `Fillet003` E2, E18, E49, E52, E56; #962's `Fillet` E6
-- upstream's behaviour on that geometry, not the pieces'. The eight that
were invalid only in pieces are fixed (../README.md, 2026-10-11). #309's
E9 (3) is made since `358d611f3f`, in pieces and refined -- the refined
shape's result was valid by BRepCheck's leave and no more: the right
surfaces, and a vertex at a tolerance of 100 (../README.md, 2026-10-13).
29 are left.

The vertex sweep's 290 at `f7464716c0` (`triage.py`): 181 invalid on the
refined shape as well -- #273 (36), #309 (14), #474 (93), #631 (2), #962
(36); 23 with an edge that is a split itself, gone from the refined shape;
and 86 valid there, invalid only in pieces. 83 of the 86 are fixed
(../README.md, 2026-10-12) and `mini_finwall`'s V11:13,26 at 1 -- two
fillets on the two pieces of a wall, one of them walked -- at `5052552dd6`
(2026-10-13); and #309's two -- V8, edges 8 and 9, at 0.3 and 1 -- with
its edge 9, at `358d611f3f`. None is left.

The 23 with a split among their edges are the sweep's "all the edges of
the vertex" where a split ends there: the builder leaves the split out, and
the fillet is that of the vertex's other edges, which the refined shape
has. 15 were invalid only in pieces after all -- three fillets at such a
vertex -- and are fixed; the 8 left hold #309's edge 9, and are made with
it at `358d611f3f`. `triage.py` took them for `noedge` then; it fillets
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
miniatures. 36 of the 50 are made at `faf4f72ee0`, 8 more at
`3ba0c94072` (../README.md, 2026-10-12) and the last 6 at `9d58debece`
(2026-10-13): #962's `Fillet` E1, the edge 0.05 long (3), and E14 at 2,
`Chamfer` E6 and E21 at 2. Two of the 14 invalid on the refined shape,
`Fillet` E5 and `Chamfer` E22 at 2, are made there and in pieces
(`7c3d8b9685`, upstream's fault).

Vertex, 2823: 2248 refused there too (24 of them with a split among their
edges), 248 `noedge`, 90 invalid there, and 237 refused only in pieces.
225 of the 237 are made at `2bc692bfc4` and the last 12 at `9d58debece`,
on #962's two inputs -- `Fillet` V1 and V2, its edge 0.05 long alone and
with a neighbour (6), and `Chamfer` V2 and V6, edge 6 at a distance of 1
(6). All four edges at a floor's corner at 1, invalid at
`3ba0c94072`, are made at `726d9533c6`, 25 pairs at `f446ee4591`, 24 at
`2ff60f1efd` (one of them, `mini_slot_bothsplit` V13:15,18 at 1, was
made invalid in between) and 23 at `2bc692bfc4`. Eight of the refused
turned invalid at `3ba0c94072`, pairs that are invalid on the refined
shape as well (V36:52,80 and the like): 200 invalid results in all
(../README.md), 201 at `9d58debece` -- `Fillet` V1:1,6 at 0.3, refused
while its edge 1 was, invalid for its edge 6, which is invalid alone, on
the refined shape too -- 200 again at `5052552dd6`, the fin's pair
above, and 176 at `358d611f3f`: the 24 with #309's edge 9, at its two
ends.

Valid for a boolean? BRepCheck's "valid" is not what the next feature
asks: a boolean takes BOP's argument check (Part's `check(True)`).
`fsw_bop.py` runs the cases a baseline has valid and puts each result to
it: `ok:<volume>:<max tol>:<faces>:c` when it reports nothing,
`...:b:<what>` when it does, `<what>` being `<shape type>/<BOP's
status>*<count>,...`. `bopin.py` puts the inputs to it first
(`baseline/inputs_bop.txt`): an input that fails it itself -- #273's
`Fillet001`, #876's `Fillet001` -- has its cases marked `input` and not
run, its results inheriting the fault (and the check of #273's taking
minutes a case). `bopcmp.py` classes an outdir by shape: clean, reported
at a tolerance of 1e-4 or less, reported looser, and what is reported;
`compare.py` takes two such runs, or one and `baseline/bop_*.txt`, and
lists every case whose verdict changed.

    FreeCADCmd bopin.py                                  # once per new input
    WORKER=fsw_bop.py SKIP=baseline/edge.txt ./drive.py edge /tmp/b_edge
    ./bopcmp.py /tmp/b_edge
    ./compare.py baseline/bop_edge.txt /tmp/b_edge

About four times a sweep's time on the mac: the edge sweep ~10 min, the
vertex sweep ~75. `baseline/bop_*.txt` is `1d642bfaaf`'s, on the cases its
own baseline has valid: edge 2398 on clean inputs, 34 reported; vertex
8858, 223 reported, 3 outlasting the 120 s -- the new reports #876's
four-edge corners at 0.3, valid since `6de00fea30` (../README.md, the
drafted boss). At `b4f2f7592c` (a fillet split only where its section is
a point) 7 edge and 49 vertex of those come clean: edge 27 reported,
vertex 174; at `892a10b753` the same; at `e549e29656` vertex 176, the
two cases it makes reported as the arc E5 alone is. `6de00fea30`'s, on the cases `a2f5c2a5d4`'s baseline had
valid: edge 2390 on clean inputs, 27 reported; vertex 8798,
172 reported, 3 outlasting the 120 s. `5c531f4938`'s: the edge sweep's
2395 valid results on clean inputs, 28 reported; the vertex sweep's 8849,
213 reported (two of #962's cases outlast the 120 s), 30 of them at 1e-4
or less. At `8558180119` it was 60 and 423 (../README.md).

The edge sweep's 27 at `e549e29656`, each made again with upstream's
TKFillet (2026-10-17):

- #474's `Fillet003` E3, E8, E16, E32, E40 at 0.3 and 0.8 (10): the
  input's sliver (../README.md, "Followed up (2026-10-03)"). Its plane
  F23 doubles back on itself, E47 lying along E49 for the 2 of their
  height the sliver face beside them takes; the fillet shortens E47, and
  its new edge ends on E49's line 7.7e-7 off, no vertex shared. Upstream
  gives the same result to the digit.
- #474's `Fillet002` E4 at 0.3 and 0.8 (2): reported upstream as well,
  at three times the tolerance.
- #273's E12, E14, E16, E18 at 0.8 and 2 (8), the handle's front edges
  down to the cylinder's rim: reported upstream as well, or worse --
  tolerances to 12.6, E16 and E18 at 2 invalid. Here at most 0.03; a
  closed edge of 3e-4 at the foot is left.
- #273's E5 and E7 (5), the arcs of the rim under the handle's front and
  back: upstream refuses them ("no suitable edges"). The two faces are
  1.6 deg from tangent and the fillet a strip 0.009 wide. At its end four
  sharp edges meet (`PerformIntersectionAtEnd`), and the rim's ledge, a
  plane, cuts the strip along its length rather than across it. The walk
  runs past the vertex as far as `ExtentOneCorner` carries the spine, half
  the edge (5.5); the line on the handle stops on its edge at the vertex,
  but the line on the cylinder, 0.004 under the rim and along it, meets no
  edge and runs on to the walk's end. The cut runs out there, at the
  surface's end rather than at a line, and an edge of 0.029 closes it to
  the rim: the ledge made again over 7.0 of its area, tolerance 0.03 --
  an artefact of the extension's length. The strip's end wants a cap in
  its section at the vertex (0.009 across, the rim's edge and the
  handle's split at its corners), a corner the builder has no form for --
  not tried; refusing a cut that runs off the surface would give
  upstream's answer.
- #273's E23 and E24 at 0.8 (2), the rims of the triangular pocket in
  the handle's top: upstream refuses them. The pocket's apex is 22 deg;
  past the fillet's analytic part the walk runs the wall's line to the
  apex while the top's swings across to the other rim, and that last
  surface folds (Face/SelfIntersect). At 0.3 it is clean.

None of them a regression of the fork's. Of the 176 vertex reports, 137
take one of these edges; the other 39 are corners -- #631's 20 (the
corner plates' section, ../README.md), #962's 12, #474's `Fillet003` 4,
#876's two four-edge corners at 0.3 and #273's V25:37,38 at 0.3 -- not
gone through so.

Valid in pieces, and the same? `fsw_ref.py` makes each case of a sweep
twice, in pieces and on the shape refined, and runs Part's `check(True)`
on both results; `refcmp.py` classes the pairs -- the same, the volume
different, BOP's check failing on one or both, the tolerance more than
ten times the refined shape's, and every other pair of statuses.

    WORKER=fsw_ref.py TIMEOUT=400 SKIP=baseline/edge.txt ./drive.py edge /tmp/f_ref [shape ...]
    ./refcmp.py /tmp/f_ref

`SKIP` names a baseline whose refused cases are not run. Two fillets and
two checks a case: several times a sweep's time, and #273's `Fillet001`
alone over an hour under BOP's check.

Run at `9d58debece`, the edge sweep on every shape but #273's
`Fillet001`: 2300 results valid on both and the same; 179 valid on both
and failing BOP's check on both, 112 of them #876's `Fillet001`, whose
input fails it by itself; 25 invalid on both; and 28 that differ --

| Results | What |
|--------:|------|
| 18 | #962's `Fillet` E49, E50, E56 and `Chamfer` E46, E47, E53: plates in pieces, tolerances of 3e-3 to 7e-2 for 1e-4, the volume off by up to 0.31, BOP's check failing on two. Exact at `6505747185` |
| 3 | #309's E9: invalid in pieces; on the refined shape valid by BRepCheck with a vertex at tolerance 100 -- counted as invalid on both, above, until this run. Made on both at `9c45825ba1` and `358d611f3f` |
| 2 | #474's `Fillet002` E13 at 0.3 and 0.8: a plate in pieces, tolerance 0.05 for 1.6e-5, BOP's check failing. Exact at `afb7f305d0` |
| 2 | #474's `Fillet002` E4: at 0.3 loose on both and failing BOP's check in pieces, at 0.8 valid in pieces and invalid refined |
| 3 | #962's `Chamfer` E12, E23, E27 at 2: volumes 0.03 to 0.08 apart at tight tolerances. The integration's, not the shapes': the fillet's face is the same on both to 1e-10, trimmed by a B-spline and parametrized the other way round, and its area comes out 107.9625 and 107.9723 |

The vertex sweep on #962's two inputs, #309, #523 and the miniatures, at
`9d58debece` and at `358d611f3f`:

| Class | `9d58debece` | `358d611f3f` |
|-------|-----:|-----:|
| valid on both, the same | 4144 | 4203 |
| valid on both, a split among the case's edges | 784 | 788 |
| valid on both, the volume different | 97 | 83 |
| valid on both, the tolerance over ten times the refined shape's | 34 | 10 |
| valid on both, BOP's check failing in pieces only | 13 | 5 |
| valid on both, BOP's check failing on both | 19 | 19 |
| invalid in pieces, valid refined (16 with #309's edge 9, at tolerance 100 there; the fin's pair of `5052552dd6`) | 17 | 0 |
| valid in pieces, invalid refined | 42 | 50 |
| valid in pieces, refused refined | 8 | 8 |
| invalid on both | 52 | 44 |
| invalid in pieces, refused refined | 1 | 1 |

What is left worse in pieces there: the 5 and the 10, pairs at a vertex
on #962 and on the arm's miniatures (0.0036 for 5e-6 at most), and those
of the 83 whose plate differs from the refined shape's exact corner
(`mini_finwall` V11:13,15 and V11:15,26 at 1, ../README.md). The
miniatures' four of the 10, and 16 of the 83, are the refined shape's at
`2ec760a1d3` (../README.md, "A line carried over a split to the pivot of
two fillets"), and the fin wall's two with 22 more set back plates like
them at `9735ff8875` ("A fillet in two surfaces at a corner of two").

A purged or misnamed input reads `MISSING` and its cases are not run: check
that both runs have every shape before reading "all the same".
