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
mkdir -p $W/before $W/after $W/home

# #64: the plane/cylinder intersection under a fuzzy value
FIX=ed990cf61b
clang++ -std=c++17 -w -I$PREFIX/include/opencascade $HERE/../models/issue064_fuzzy_plane_cylinder.cpp \
    -L$PREFIX/lib -Wl,-rpath,$PREFIX/lib -lTKBO -lTKPrim -lTKTopAlgo -lTKBRep -lTKGeomAlgo \
    -lTKGeomBase -lTKG3d -lTKG2d -lTKMath -lTKernel -o $W/issue064
[ -e $W/old064/libTKGeomBase.8.0.dylib ] || [ -e $W/old064/libTKGeomBase.so.8.0 ] ||
    python3 $HERE/mkold.py $BUILD $W/old064 "$FIX^" \
        src/ModelingData/TKGeomBase/IntAna/IntAna_QuadQuadGeo.cxx > $W/mkold064.log 2>&1
# before the fix the driver fails (exit 1): its results are the point
DYLD_LIBRARY_PATH=$W/old064 LD_LIBRARY_PATH=$W/old064 $W/issue064 --write $W/before > $W/before.txt || true
$W/issue064 --write $W/after > $W/after.txt
grep -q "^0 bad" $W/after.txt || { echo "the driver fails after the fix, see $W/after.txt"; exit 1; }

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
