# The draft sweep

The regression sweep of fcad `docs/NewDraft.md` (sections 10.2 onward): every
draft case below through PartDesign's Draft, against a baseline. Run it
before and after any change to `Part::CellDraft`; what is not meant to move
must come out the same.

| List | Cases | What |
|------|------:|------|
| `classic_valid.lst` | 1222 | drafts the classic draft makes valid |
| `classic_refused.lst` | 500 | drafts the classic draft refuses (Auto's fallback) |
| `chains.lst` | 114 | drafts whose face has a tangent chain (run with `PROP=0` for section 17) |

Lines are `shape face neutral angle`; `shapes/` holds the 25 inputs (the
features' base shapes from `../../occ-issues/models` and a few minimal ones;
`issue962_Fillet` is `../../fillet/models/issue962_pocket002.brep`).

    ./drive.py classic_valid.lst /tmp/out_ok New 1           # ~10 min on the mac
    ./compare.py baseline/classic_valid.txt /tmp/out_ok
    PROP=0 ./drive.py chains.lst /tmp/out_ch New 1
    ./compare.py baseline/chains_nopropagate.txt /tmp/out_ch

`drive.py <list> <outdir> [Method] [StopAtBody]`, env `FCBUILD`, `RUN`, `PROP`,
`TKF` (a directory of OCCT libraries loaded first -- a rebuilt TKFillet tried
without installing it; macOS strips `DYLD_*` from a bash script's children,
so it is set inside `RUN`). One FreeCADCmd per shape, one at a time (8 GB box).
A result is `ok:volume:faces:bopclean` (the last is Part's `check(True)`) or
`FAIL(why)`. `compare.py` classes the changes; `SHOW=n` lists n of each.

`baseline/` is fcad OcctFix `3b1f9a37cb` (2026-10-09), `Method = New`, the
stop on: `classic_valid` and `classic_refused` with propagation on,
`chains_nopropagate` with it off.

A purged input makes every case `TIMEOUT/CRASH` on both builds, and a
comparison then reads "all the same": check that the results are real.

## tools/

- `fil.cpp`: `BRepFilletAPI_MakeFillet` on a BRep, and what it says when it
  fails (stripe status, faulty contours and vertices); the edges by the
  points nearest their middles, or `pair nx ny nz mx my mz` for the edges
  between two planes; `CHECK=1` lists BRepCheck's complaints, `OUTB=` writes
  the result.

      O=~/works/sw/occt/install/conda-relwithdebinfo-801
      clang++ -std=c++17 -g -O0 -w -I$O/include/opencascade fil.cpp -L$O/lib \
        -lTKernel -lTKMath -lTKG3d -lTKBRep -lTKTopAlgo -lTKFillet -lTKGeomBase \
        -Wl,-rpath,$O/lib -o fil

- `throwbt.cpp`: a dylib interposing `__cxa_throw`, printing each throw
  site's backtrace (library and offset; `atos -o <lib> -l 0 <offset-1>` gives
  the line). lldb cannot run non-interactively on the mac (developer mode).

      clang++ -dynamiclib throwbt.cpp -o throwbt.dylib
      DYLD_INSERT_LIBRARIES=$PWD/throwbt.dylib ./fil ...
