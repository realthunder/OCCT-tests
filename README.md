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
FreeCADCmd tests/fork/boolean/run_tests.py
```

On another OCCT than the fork -- upstream's, as FreeCAD can load it -- every
case would fail for want of the fork, so each suite says "SKIP: not the OCCT
fork" and exits 0. The fork is found as FreeCAD finds it, by a C function of
its TKBRep (`Part.hasOCCTFunction("TKBRep", "SetFuncShowTopoShape")`).

- `thickness/` -- the thickness (`BRepOffsetAPI_MakeThickSolid`) suite:
  `run_tests.py`, the sweep, the captured models, `models/Thickness.md`
  (every fix, before and after) and its pictures.
- `fillet/` -- the fillet suite, laid out the same way, `models/Fillet.md`.
- `draft/` -- the draft (`BRepOffsetAPI_DraftAngle`) suite: `run_tests.py`,
  its README, `models/Draft.md` and a few models of its own; most of its
  models are `occ-issues/`'s. The fillet and draft suites also read each
  other's `models/` and the draft sweep's `sweep/shapes/`.
- `boolean/` -- the fixes met through the booleans and the general fuse
  (and the surface intersections they call), most from `occ-issues/`:
  `run_tests.py`, a C++ driver of each fix in `models/`, the write-up of
  each in its README, and its pictures (before and after).
- `exchange/` -- the fixes to reading and writing STEP and the other
  formats, and the shape processing they run: a C++ driver of each fix in
  `models/`, the write-up of each in its README, and its pictures.
- `occ-issues/` -- every issue labelled `occ` on realthunder/FreeCAD, with
  the models attached to it and a scan of each.
- `surface/` -- checks of the curve network surfaces (`GeomFill_Gordon`,
  `GeomFill_NetworkSurface`): a C++ driver each, and the write-up of each
  fix in its README.
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

## A fix that changes a shape

The rule for every fix to the fork (the user's ruling, 2026-10-29). Run
the suites over it, each frozen and unfrozen. If it changes no result a
suite already had -- no volume, no validity, no case -- it lands as the
fork's behaviour. So does one whose changes stay within the tolerances of
the shapes it changes (the user's, the same day): measure them to full
precision, not to the four places the suites print -- how far each changed
shape moves, against its tolerance there. If it changes any result past
that, it goes behind an option, off by
default, so that the shape a document saved comes back as it was; FreeCAD
turns the option on for objects made from then on, and keeps it off for an
object an older file brings (a hidden property of the object, 0 when the
file has not got it). The option keeps the ABI (`abi/`): a C function
FreeCAD looks up by name, not a member, a parameter or a virtual function
of a class of upstream's.

For the offset and thickness that option is a level,
`BRepOffset_SetFixLevel(n)` (`BRepOffset.hxx`): the calling thread's, 0 by
default, each level adding its fixes to those below. FreeCAD holds a
feature's `_OffsetFixLevel` for the feature's recompute
(`Part::OCCTOffsetFixLevel`, `src/Mod/Part/App/OCCTFork.h`), and a new
level is a new value of `Part::OCCTOffsetFixLevelLatest` there. The suites
set it with `THICK_FIX_LEVEL=<n>` or per case (`fix_level.py`); a fix
behind a level is run at 0, where nothing may change, and at the latest.
Level 1 brought the filleted dome outward (`thickness/models/Thickness.md`
sec 31); measured, it moved the shapes before it within their tolerances,
so it is made at every level now and level 1 makes nothing differently. It
stays reserved, since FreeCAD has saved objects at 1: the next level is 2
(sec 32).

History: moved out of the fork on 2026-10-03 with its history (the fork's
`tests/thickness/`, `tests/fillet/` and `tests/occ-issues/`); the commits
here are those, rewritten by `git filter-repo`.
