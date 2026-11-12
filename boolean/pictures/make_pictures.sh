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

LIBS="-lTKOffset -lTKBO -lTKPrim -lTKTopAlgo -lTKBRep -lTKGeomAlgo -lTKGeomBase -lTKG3d -lTKG2d"
LIBS="$LIBS -lTKMath -lTKernel"
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
# fix <tag> <commit> <source> <driver> [args]: the driver built against the
# install, run on the library <source> belongs to as it was before <commit>
# (mkold.py) into $W/<tag>/before -- it fails there (exit 1): its results are
# the point -- and on the install into $W/<tag>/after, where it must pass.
fix() {
    local tag=$1 commit=$2 src=$3 drv=$4
    shift 4
    mkdir -p $W/$tag/before $W/$tag/after
    $CXX -std=c++17 -w -I$PREFIX/include/opencascade $HERE/../models/$drv.cpp \
        -L$PREFIX/lib $LIBS -o $W/$tag/$drv
    ls $W/$tag/old/lib* > /dev/null 2>&1 ||
        $INENV python3 $HERE/mkold.py $BUILD $W/$tag/old "$commit^" $src > $W/$tag/mkold.log 2>&1
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
# a section's tangent end at a corner: the offsets of two fillets of a dome
fix dome e9ded0215d src/ModelingAlgorithms/TKBO/BOPAlgo/BOPAlgo_PaveFiller_6.cxx \
    dome_tangent_corner $HERE/../models/dome_fillet_r3.brep --write
# #617: the volume and area integrals of two B-spline prisms, span by span
fix 617 2c45873435 src/ModelingAlgorithms/TKTopAlgo/BRepGProp/BRepGProp_Gauss.cxx \
    issue617_gprop_prism $HERE/../models/issue617_revolution.brep --write
# an offset surface's integrals in pieces where its normal turns unevenly
fix off 54de50c4c1 src/ModelingAlgorithms/TKTopAlgo/BRepGProp/BRepGProp_Gauss.cxx \
    offset_surface_gprop --write
# an ellipse's extrusion and revolution: their area in pieces where the normal turns unevenly
fix ext 8655926813 src/ModelingAlgorithms/TKTopAlgo/BRepGProp/BRepGProp_Gauss.cxx \
    extrusion_area_gprop --write
fix knots 66c168acc5 src/ModelingAlgorithms/TKTopAlgo/BRepGProp/BRepGProp_Gauss.cxx \
    bspline_knots_gprop --write
# the adaptive integrals refined across u, from the plain integral's breaks
fix adapt 15ce0973f6 src/ModelingAlgorithms/TKTopAlgo/BRepGProp/BRepGProp_Gauss.cxx \
    adaptive_gprop $HERE/../models/issue617_prisms.brep --write
# #617: the pad's bottom edge projected across the revolution's closed seam
fix 617seam 3c35c64037 "src/ModelingData/TKGeomBase/ProjLib/ProjLib_CompProjectedCurve.cxx \
    src/ModelingData/TKGeomBase/ProjLib/ProjLib_ProjectedCurve.cxx" issue617_seam_pcurve \
    $HERE/../models/issue617_revolution.brep $HERE/../models/issue617_prisms.brep --write
# #617: the Pad's fuse, a wall standing on the revolution along its bottom edge
fix 617pad 11d03d433c "src/ModelingAlgorithms/TKBO/BOPAlgo/BOPAlgo_PaveFiller_5.cxx \
    src/ModelingAlgorithms/TKBO/BOPAlgo/BOPAlgo_PaveFiller_6.cxx" issue617_pad_fuse \
    $HERE/../models/issue617_revolution.brep $HERE/../models/issue617_prisms.brep --write
# #280: the Pocket's cut, a section that stops short of the corner it runs into
fix 280 c861b8b553 src/ModelingAlgorithms/TKBO/BOPAlgo/BOPAlgo_PaveFiller_6.cxx \
    issue280_pocket_cut $HERE/../models/issue280_part.brep $HERE/../models/issue280_tool.brep \
    --write

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
