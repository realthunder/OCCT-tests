# The OCCT fork's own tests

The test suites, models, write-ups and pictures that realthunder/OCCT
(branch `LinkVibe-801`) adds to OCCT. The fork mounts this repository as a
submodule at `tests/fork`; upstream's own tests stay where they are in
the fork.

```
git submodule update --init tests/fork     # once per clone of the fork
FreeCADCmd tests/fork/thickness/run_tests.py
FreeCADCmd tests/fork/fillet/run_tests.py
FreeCADCmd tests/fork/draft/run_tests.py
```

On another OCCT than the fork -- upstream's, as FreeCAD can load it -- every
case would fail for want of the fork, so each suite says "SKIP: not the OCCT
fork" and exits 0. The fork is found as FreeCAD finds it, by a C function of
its TKBRep (`Part.hasOCCTFunction("TKBRep", "SetFuncShowTopoShape")`).

- `thickness/` -- the thickness (`BRepOffsetAPI_MakeThickSolid`) suite:
  `run_tests.py`, the sweep, the captured models, `models/Thickness.md`
  (every fix, before and after) and its pictures.
- `fillet/` -- the fillet suite, laid out the same way, `models/Fillet.md`.
- `draft/` -- the draft (`BRepOffsetAPI_DraftAngle`) suite: `run_tests.py`
  and its README; its models are `occ-issues/`'s.
- `occ-issues/` -- every issue labelled `occ` on realthunder/FreeCAD, with
  the models attached to it and a scan of each.
- `math/` -- checks of `TKMath` the work on the others led to: a C++
  driver each, built against an install.
- `abi/` -- the fork against upstream's ABI: the symbols upstream exports
  and the layouts of the classes the fork changed, checked against an
  upstream build, and how to add to a class of upstream's without moving it.

`loose_ends.py` is a check the suites and sweeps share: an edge whose 3D
curve, at an end of its parameter range, misses its vertex by more than ten
times the edge's tolerance (and 1e-4). BRepCheck measures that gap against
the vertex's tolerance, so a vertex raised to cover it passes -- and BOP's
argument check too. x16win's chamfer at a corner of two fillets
(`fillet/README.md`) made such a solid: three edges 0.3819 short of their
vertices, the vertices at 0.382, the volume 45.6 out, "valid". Every result
a suite makes is checked; a sweep marks such a result `LOOSE` in place of
`ok`.

The pictures are made again after every fix; their history grows here, not
in the fork's.

Every suite here is added to by the work on the fork: a fix lands in the
fork, its cases and pictures here, and the fork's commit moves the
submodule to the matching commit.

History: moved out of the fork on 2026-10-03 with its history (the fork's
`tests/thickness/`, `tests/fillet/` and `tests/occ-issues/`); the commits
here are those, rewritten by `git filter-repo`.
