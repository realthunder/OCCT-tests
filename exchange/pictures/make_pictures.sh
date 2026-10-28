#!/bin/bash
# make_pictures.sh -- regenerate models/pictures (README.md).
#
# Builds the C++ driver of each fix against the install, links the library
# the fix changed as it was just before it (../../boolean/pictures/mkold.py:
# from the build tree's own objects, nothing installed is touched), runs the
# driver on both, lays the shapes it read back out as panels (prep.py),
# renders them in the FreeCAD GUI (../../fillet/pictures/render.py) and
# composes the picture (../../boolean/pictures/compose.py).
#
# env: EXCH_WORK  scratch directory (default /tmp/exchange-pictures)
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
export W=${EXCH_WORK:-/tmp/exchange-pictures}
mkdir -p $W/home

LIBS="-lTKDESTEP -lTKXCAF -lTKLCAF -lTKCAF -lTKCDF -lTKXSBase -lTKShHealing -lTKPrim -lTKTopAlgo"
LIBS="$LIBS -lTKBRep -lTKGeomAlgo -lTKGeomBase -lTKG3d -lTKG2d -lTKMath -lTKernel"
LIBS="$LIBS -lTKService -lTKV3d"
# fix <tag> <commit> <source> <driver>: the driver built against the install,
# run on the library <source> belongs to as it was before <commit> into
# $W/<tag>/before -- it fails there (exit 1): its results are the point --
# and on the install into $W/<tag>/after, where it must pass.
fix() {
    local tag=$1 commit=$2 src=$3 drv=$4
    mkdir -p $W/$tag/before $W/$tag/after
    clang++ -std=c++17 -w -I$PREFIX/include/opencascade $HERE/../models/$drv.cpp \
        -L$PREFIX/lib -Wl,-rpath,$PREFIX/lib $LIBS -o $W/$tag/$drv
    ls $W/$tag/old/lib* > /dev/null 2>&1 ||
        python3 $HERE/../../boolean/pictures/mkold.py $BUILD $W/$tag/old "$commit^" $src \
            > $W/$tag/mkold.log 2>&1
    DYLD_LIBRARY_PATH=$W/$tag/old LD_LIBRARY_PATH=$W/$tag/old $W/$tag/$drv $W/$tag/before \
        > $W/$tag/before.txt 2>&1 || true
    $W/$tag/$drv $W/$tag/after > $W/$tag/after.txt 2>&1 ||
        { echo "$drv fails after the fix, see $W/$tag/after.txt"; exit 1; }
}
# #310: a STEP colour kept on its face when another face is its partner
fix 310 9ba3806e9b src/ModelingAlgorithms/TKShHealing/ShapeProcess/ShapeProcess_ShapeContext.cxx \
    issue310_step_partner_colours

python3 $HERE/prep.py > $W/prep.log 2>&1
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
