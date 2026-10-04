#!/bin/bash
# make_sliver.sh -- models/pictures/arc_join_sliver.png (Thickness.md sec 25):
# the exact answer of the Arc join built from primitives, and the sliver face
# it has at each end of the tangent edge, which the fork does not build.
#
# env: OUT      scratch directory (default /tmp/thickness-sliver)
#      FCBUILD  a FreeCAD build; RUN the wrapper that runs a command in its
#               environment (as make_pictures.sh)
set -e
HERE=$(cd $(dirname $0) && pwd)
RUN=${RUN:-$HOME/works/sw/fcad/.conda/run.sh}
FCBUILD=${FCBUILD:-$HOME/works/sw/fcad/build/conda-relwithdebinfo-801}
export OUT=${OUT:-/tmp/thickness-sliver}
mkdir -p $OUT/home
FREECAD_USER_HOME=$OUT/home $RUN $FCBUILD/bin/FreeCADCmd $HERE/build.py > $OUT/build.log 2>&1
grep -q '^DONE' $OUT/build.log || { echo "build failed, see $OUT/build.log"; exit 1; }
(ulimit -v 20000000
 FREECAD_USER_HOME=$OUT/home xvfb-run -a -s "-screen 0 1600x1200x24" \
     $RUN $FCBUILD/bin/FreeCAD $HERE/render.py > $OUT/render.log 2>&1) || true
grep -q '^DONE' $OUT/render.log || { echo "render failed, see $OUT/render.log"; exit 1; }
$RUN python $HERE/compose.py
cp $OUT/arc_join_sliver.png $HERE/../../models/pictures/arc_join_sliver.png
