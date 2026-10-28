#!/bin/bash
# make_pictures.sh -- regenerate models/pictures (README.md).
#
# Builds the C++ driver of each fix against the install, links the library
# the fix changed as it was just before it (mkold.py: from the build tree's
# own objects, nothing installed is touched), runs the driver on both
# (--write), lays the results out as panels (prep.py, FreeCADCmd), renders
# them in the FreeCAD GUI (../../fillet/pictures/render.py) and composes the
# picture (compose.py).
#
# env: BOOL_WORK  scratch directory (default /tmp/boolean-pictures)
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
export W=${BOOL_WORK:-/tmp/boolean-pictures}
mkdir -p $W/home

LIBS="-lTKBO -lTKPrim -lTKTopAlgo -lTKBRep -lTKGeomAlgo -lTKGeomBase -lTKG3d -lTKG2d"
LIBS="$LIBS -lTKMath -lTKernel"
# fix <tag> <commit> <source> <driver> [args]: the driver built against the
# install, run on the library <source> belongs to as it was before <commit>
# (mkold.py) into $W/<tag>/before -- it fails there (exit 1): its results are
# the point -- and on the install into $W/<tag>/after, where it must pass.
fix() {
    local tag=$1 commit=$2 src=$3 drv=$4
    shift 4
    mkdir -p $W/$tag/before $W/$tag/after
    clang++ -std=c++17 -w -I$PREFIX/include/opencascade $HERE/../models/$drv.cpp \
        -L$PREFIX/lib -Wl,-rpath,$PREFIX/lib $LIBS -o $W/$tag/$drv
    ls $W/$tag/old/lib* > /dev/null 2>&1 ||
        python3 $HERE/mkold.py $BUILD $W/$tag/old "$commit^" $src > $W/$tag/mkold.log 2>&1
    DYLD_LIBRARY_PATH=$W/$tag/old LD_LIBRARY_PATH=$W/$tag/old $W/$tag/$drv "$@" $W/$tag/before \
        > $W/$tag/before.txt || true
    $W/$tag/$drv "$@" $W/$tag/after > $W/$tag/after.txt ||
        { echo "$drv fails after the fix, see $W/$tag/after.txt"; exit 1; }
}
# #64: the plane/cylinder intersection under a fuzzy value
fix 064 ed990cf61b src/ModelingData/TKGeomBase/IntAna/IntAna_QuadQuadGeo.cxx \
    issue064_fuzzy_plane_cylinder --write
# #613: a section whose end vertex lies a hair in, closed
fix 613 59ca72bbcc src/ModelingAlgorithms/TKBO/BOPAlgo/BOPAlgo_PaveFiller_6.cxx \
    issue613_seam_section --write
# #580: a degenerated edge's pcurve on a plane kept by a transformed copy
fix 580 c20f921783 src/ModelingData/TKBRep/BRepTools/BRepTools_TrsfModification.cxx \
    issue580_mirror_degenerated $HERE/../models/issue580_pad003.brep --write

FREECAD_USER_HOME=$W/home $RUN $FCBUILD/bin/FreeCADCmd $HERE/prep.py > $W/prep.log 2>&1
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
$RUN python $HERE/compose.py ${OUTDIR:-$HERE/../models/pictures}
