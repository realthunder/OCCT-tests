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

- `thickness/` -- the thickness (`BRepOffsetAPI_MakeThickSolid`) suite:
  `run_tests.py`, the sweep, the captured models, `models/Thickness.md`
  (every fix, before and after) and its pictures.
- `fillet/` -- the fillet suite, laid out the same way, `models/Fillet.md`.
- `draft/` -- the draft (`BRepOffsetAPI_DraftAngle`) suite: `run_tests.py`
  and its README; its models are `occ-issues/`'s.
- `occ-issues/` -- every issue labelled `occ` on realthunder/FreeCAD, with
  the models attached to it and a scan of each.

The pictures are made again after every fix; their history grows here, not
in the fork's.

Every suite here is added to by the work on the fork: a fix lands in the
fork, its cases and pictures here, and the fork's commit moves the
submodule to the matching commit.

History: moved out of the fork on 2026-10-03 with its history (the fork's
`tests/thickness/`, `tests/fillet/` and `tests/occ-issues/`); the commits
here are those, rewritten by `git filter-repo`.
