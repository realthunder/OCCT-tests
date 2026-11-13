#!/bin/bash
# make_fix_pictures.sh -- the pictures of the fixes with a C++ driver in
# models/ (README.md, #363), before and after, on macOS or Linux; the cases of
# cases.py have make_pictures.sh.
#
# Builds the driver of each fix against the install, links the library the
# fix changed as it was just before it (../../boolean/pictures/mkold.py: from
# the build tree's own objects, nothing installed is touched), runs the driver
# on both (--write), lays the results out as panels (prep_fixes.py,
# FreeCADCmd), renders them in the FreeCAD GUI (../../fillet/pictures/render.py)
# and composes the picture (../../boolean/pictures/compose.py).
#
# env: FIX_WORK   scratch directory (default /tmp/thickness-fix-pictures)
#      OCCT       the fork's checkout (default: this submodule's superproject)
#      BUILD      its build tree (default $OCCT/build_conda_rwdi_801)
#      PREFIX     its install (default $OCCT/install/conda-relwithdebinfo-801)
#      FCBUILD    a FreeCAD build linked against that install
#      RUN        the wrapper that runs a command in the build's environment
#      OUTDIR     where the pictures go (default ../models/pictures)
set -e
HERE=$(cd $(dirname $0) && pwd)
OCCT=${OCCT:-$(cd $HERE && git rev-parse --show-superproject-working-tree)}
BUILD=${BUILD:-$OCCT/build_conda_rwdi_801}
PREFIX=${PREFIX:-$OCCT/install/conda-relwithdebinfo-801}
RUN=${RUN:-$HOME/works/sw/fcad/.conda/run.sh}
if [ "$(uname)" = Darwin ]; then
    FCBUILD=${FCBUILD:-$HOME/works/sw/fcad/build/mac-relwithdebinfo-801}
else
    FCBUILD=${FCBUILD:-$HOME/works/sw/fcad/build/conda-relwithdebinfo-801}
fi
export W=${FIX_WORK:-/tmp/thickness-fix-pictures}
mkdir -p $W/home

LIBS="-lTKOffset -lTKFillet -lTKBO -lTKPrim -lTKTopAlgo -lTKBRep -lTKGeomAlgo -lTKGeomBase"
LIBS="$LIBS -lTKG3d -lTKG2d -lTKMath -lTKernel"
# On Linux the driver's rpath must be a RUNPATH, or LD_LIBRARY_PATH cannot put
# the old library first (a DT_RPATH, which conda's linker writes, outranks it)
# and "before" silently runs the install.
if [ "$(uname)" = Darwin ]; then
    CXX=${CXX:-clang++}
    LIBS="$LIBS -Wl,-rpath,$PREFIX/lib"
else
    # the env's compiler, for the libstdc++ the install was built with
    CXX=${CXX:-"$RUN x86_64-conda-linux-gnu-c++"}
    LIBS="$LIBS -Wl,--enable-new-dtags -Wl,-rpath,$PREFIX/lib"
    # ninja and the build's compilers are the env's
    INENV=$RUN
fi
# fix <tag> <commit> <sources> <driver> [args]: the driver built against the
# install, run on the library <sources> (one word, or several in one quoted
# argument) belong to, as they were before <commit>,
# into $W/<tag>/before -- it fails there (exit 1): its results are the point --
# and on the install into $W/<tag>/after, where it must pass.
fix() {
    local tag=$1 commit=$2 src=$3 drv=$4
    shift 4
    mkdir -p $W/$tag/before $W/$tag/after
    $CXX -std=c++17 -w -I$PREFIX/include/opencascade $HERE/../models/$drv.cpp \
        -L$PREFIX/lib $LIBS -o $W/$tag/$drv
    ls $W/$tag/old/lib* > /dev/null 2>&1 ||
        $INENV python3 $HERE/../../boolean/pictures/mkold.py $BUILD $W/$tag/old "$commit^" $src \
            > $W/$tag/mkold.log 2>&1
    # On Linux the old library is preloaded as well: one the driver reaches
    # through another (TKBool, through TKOffset) is looked for by that one's
    # DT_RPATH, its own directory, before LD_LIBRARY_PATH -- and "before" ran
    # the install.
    local pre=""
    [ "$(uname)" = Linux ] && pre=$(ls $W/$tag/old/lib*.so.8.0 | head -1)
    DYLD_LIBRARY_PATH=$W/$tag/old LD_LIBRARY_PATH=$W/$tag/old LD_PRELOAD=$pre \
        $W/$tag/$drv "$@" $W/$tag/before > $W/$tag/before.txt 2>&1 || true
    $W/$tag/$drv "$@" $W/$tag/after > $W/$tag/after.txt 2>&1 ||
        { echo "$drv fails after the fix, see $W/$tag/after.txt"; exit 1; }
}
# #363: two offset faces sharing two edges apart, intersected for one of them
# (5525e72804), and arcs of one circle on removed faces each stretched round it
# (0c1693fb61): before the first, both sources as they were
fix 363 5525e72804 "src/ModelingAlgorithms/TKOffset/BRepOffset/BRepOffset_Inter3d.cxx
    src/ModelingAlgorithms/TKOffset/BRepOffset/BRepOffset_Tool.cxx" issue363_groove --write
# a filleted dome outward: offset faces share a vertex where their offsets of
# it meet
fix dome 8097862fb0 src/ModelingAlgorithms/TKOffset/BRepOffset/BRepOffset_MakeOffset.cxx \
    dome_crease_fades $HERE/../../boolean/models/dome_fillet_r3.brep --write
# a filleted dome, the dome removed: tubes round its tangent edges built and
# joined (three sources)
fix domecap 6004240f16 "src/ModelingAlgorithms/TKOffset/BRepOffset/BRepOffset_MakeOffset.cxx
    src/ModelingAlgorithms/TKOffset/BRepOffset/BRepOffset_Inter2d.cxx
    src/ModelingAlgorithms/TKOffset/BRepOffset/BRepOffset_Tool.cxx" \
    dome_cap_removed $HERE/../../boolean/models/dome_fillet_r3.brep --write
# the same, outward: no corner sphere where two tubes meet, no section of one
# vertex, a merged vertex replaced on every face (TKOffset, three sources; the
# two TKBool fixes c8e8866490 and 29f01c8d95 come from the install either way)
fix domecapout b16d138042 "src/ModelingAlgorithms/TKOffset/BRepOffset/BRepOffset_MakeLoops.cxx
    src/ModelingAlgorithms/TKOffset/BRepOffset/BRepOffset_MakeOffset.cxx
    src/ModelingAlgorithms/TKOffset/BRepOffset/BRepOffset_Tool.cxx" \
    dome_cap_removed $HERE/../../boolean/models/dome_fillet_r3.brep --write

# #346: an offset inward where a dome comes to a point -- a gap at a dimple
# left open for the sphere round the apex, the seam trimmed at an apex
# crossed given its range (both sources)
fix 346 e306bb1ae4 "src/ModelingAlgorithms/TKOffset/BRepOffset/BRepOffset_Offset.cxx
    src/ModelingAlgorithms/TKOffset/BRepOffset/BRepOffset_MakeOffset.cxx" \
    issue346_offset $HERE/../models/issue346_revolve.brep --write

# #613's part, a flat of its roof removed: two tubes going on from each other
# share their end (40ddbee82b, TKOffset), and an edge's direction at a vertex is
# the chord's where the pcurve's end tangent strays (575b0f6c53, TKBool)
fix 613flat15 40ddbee82b src/ModelingAlgorithms/TKOffset/BRepOffset/BRepOffset_MakeOffset.cxx \
    issue613_roof_flat $HERE/../models/issue613_fillet.brep 15 --write
fix 613flat21 575b0f6c53 src/ModelingAlgorithms/TKBool/BRepAlgo/BRepAlgo_Loop.cxx \
    issue613_roof_flat $HERE/../models/issue613_fillet.brep 21 --write

FREECAD_USER_HOME=$W/home $RUN $FCBUILD/bin/FreeCADCmd $HERE/prep_fixes.py > $W/prep.log 2>&1
grep -q '^DONE' $W/prep.log || { echo "prep failed, see $W/prep.log"; exit 1; }
if [ "$(uname)" = Darwin ]; then
    # a .py given to the GUI opens in the editor on macOS; a macro runs
    cp $HERE/../../fillet/pictures/render.py $W/render.FCMacro
    JOBS=$W/jobs.json FREECAD_USER_HOME=$W/home $RUN $FCBUILD/bin/FreeCAD \
        $W/render.FCMacro > $W/render.log 2>&1
else
    JOBS=$W/jobs.json FREECAD_USER_HOME=$W/home xvfb-run -a -s "-screen 0 1600x1200x24" \
        $RUN $FCBUILD/bin/FreeCAD $HERE/../../fillet/pictures/render.py > $W/render.log 2>&1
fi
grep -q '^DONE' $W/render.log || { echo "render failed, see $W/render.log"; exit 1; }
$RUN python $HERE/../../boolean/pictures/compose.py ${OUTDIR:-$HERE/../models/pictures}
