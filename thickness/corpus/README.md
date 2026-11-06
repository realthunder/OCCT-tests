# The thickness corpus

A wider net than `run_tests.py`, for checking that a BRepOffset fix moves only
what it means to move. Each face of each shape is removed in turn, at +1, -1, +0.5
and -0.5, with both joins, and the whole shape is offset too: 1072 runs. Each one
prints a single line: `done valid V solids N vol X`, `not done`, or `threw`.
Pure C++ (no FreeCAD), so it runs beside a FreeCAD job.

    CXX=clang++ ./build.sh <occt install prefix> bin    # once per OCCT install
    ./corpus.sh bin > new.txt                           # the install's libraries
    ./corpus.sh bin DYLD_LIBRARY_PATH=/path/lib > new.txt   # a staged TKOffset (LD_ on Linux)
    diff <(perl -pe 's/ [0-9.]+s$//' baseline.txt) <(perl -pe 's/ [0-9.]+s$//' new.txt)

To test a change before installing it, build only `TKOffset`, copy its
`libTKOffset.8.0.*` into a fresh directory and point the library path there.
Every other library still comes from the install, so don't install while a corpus
run is going.

On Linux the tools are linked with `--enable-new-dtags`: their rpath is then a
RUNPATH, which the library path outranks. conda's linker writes a DT_RPATH
otherwise, which outranks the library path, and a staged library is silently
not the one run. conda's env activation sets `CXX`, so give it inside the env:

    run.sh bash -c "CXX=x86_64-conda-linux-gnu-c++ ./build.sh <prefix> bin"

FreeCAD itself carries a DT_RPATH to the OCCT it was built with, so a staged
library does not reach it: a FreeCAD-level test of a change needs it installed
into a prefix of its own and a FreeCAD built against that.

On Linux (2026-11-06, the fork at sec 54) 14 runs of `baseline.txt`, which
macOS made, come out otherwise: #346's profile revolved about axes shifted by
+3 and -3 with f1 removed (`rev3`, `rev-3` and their `revs` twins). macOS makes
`rev3`'s at +-1 and +-0.5 with the Arc join and refuses `rev-3`'s; Linux makes
`rev-3`'s (at +1 and +0.5) and refuses `rev3`'s, and makes `rev-3` -1 with the
Intersection join invalid. The two shapes mirror each other: the revolve
family's outcome turns on a hair. Compare a run with one from the same
platform.

`baseline.txt` is the fork's current result (timings stripped). A fix changes it
only in the runs it means to make. Note each change in the fix's README section
(the "Over the corpus (1072 runs) N change" line), and commit the new baseline
with the fix.

## The shapes

- `../models/issue346_revolve.brep`: #346's revolve.
- `breps/`: #363's cylinder with a square step cut off its end (`cside`) and a
  square slot across it (`cslot`); the grooved cylinders, groove radius 5 or 10
  (`g5`, `g10`), the latter with the top chamfered (`chg10`); the box with a groove
  (`bg10`) and with a slot (`bslot`); #363's Thickness001 base (`t001`); #521's
  Connect (`i521`); #613's model (`t613`).
- `breps/apex/`: surfaces that reach their axis. The cone, the sphere, the
  spindle torus (made by `mkapex`), and #346's profile revolved about axes shifted
  by -3, -1.05, 0, 1.05 and 3 (`rev*`; `revs*` close it with a sphere).

## The tools

Built by `build.sh` from `tools/`. Face and vertex indices are 1-based, in
`TopExp::MapShapes` order, which is FreeCAD's `Faces[i - 1]` too.

| Tool | What it does |
|------|--------------|
| `thk <brep> <off> <join> <inter> <faces...>` | MakeThickSolidByJoin, Skin; join 0 Arc, nonzero Intersection; `OUT=file` writes the result |
| `offs <brep> <off> <join> <inter>` | MakeOffsetShape of the whole; `OUT=` |
| `thke2` | `thk`, also printing MakeOffset's error code |
| `thkm2 <brep> <off> <join> <inter> <f1,f2,...>` | `thk` with the debug dumps: `SHOWKEYS="file.cxx ..."` prints the `SHOW_TOPO_SHAPE` points in those sources, `SHOWSAVE=dir` writes each shape shown |
| `faces`, `fedges`, `fchk` | faces: surface, area, wires, edges, BRepCheck |
| `ax3`, `urange`, `edom`, `sinfo` | surfaces' frames, bounds and domains |
| `fpc2`, `epc`, `vuse`, `vnear` | pcurves; what each vertex is on |
| `euse`, `loose` | edges not used once each way round; curve ends off their vertices |
| `vol`, `gvol`, `meshvol` | volumes: adaptive, plain, by a fine mesh |
| `offrw` | an offset's validity before and after a BRep text round trip |
| `mkapex <kind> <out>` | the cone, sphere and spindle of `breps/apex/` |
