#!/bin/bash
# probe.sh <outdir> [shapes...]  -- probe.py for each shape (all of shapes.py
# when none is named), six at a time; then a line a shape of what it found.
# env: FCBUILD  a FreeCAD build linked against this OCCT tree
#      RUN      the wrapper that runs a command in the build's environment
#      LIBN     a directory whose TKGeomAlgo, TKBool and TKOffset are preloaded
#      N, TOL, JOINS, SKIP  as probe.py
HERE=$(cd $(dirname $0) && pwd)
RUN=${RUN:-$HOME/works/sw/fcad/.conda/run.sh}
FCBUILD=${FCBUILD:-$HOME/works/sw/fcad/build/conda-relwithdebinfo-801}
O=$1; shift
mkdir -p $O/home
[ $# -eq 0 ] && set -- $(python3 -c "import re; print(' '.join(re.findall(r'\"([a-z0-9_]+)\":', open('$HERE/shapes.py').read().split('SHAPES = {')[1])))")
PRE=""
for l in TKGeomAlgo TKBool TKOffset; do
    [ -n "$LIBN" ] && PRE="$PRE $LIBN/lib$l.so.8.0.1"
done
export FREECAD_USER_HOME=$O/home MALLOC_ARENA_MAX=8 OPENBLAS_NUM_THREADS=1
for n in "$@"; do
    while [ $(jobs -r | wc -l) -ge 6 ]; do wait -n; done
    ( SHAPE=$n OUT=$O/$n.txt timeout 3000 $RUN env LD_PRELOAD="$PRE" \
        $FCBUILD/bin/FreeCADCmd $HERE/probe.py > $O/$n.log 2>&1 ) &
done
wait
for f in $O/*.txt; do
    a() { grep " j0 " $f | grep -c "$1"; }; b() { grep " j2 " $f | grep -c "$1"; }
    F="%-18s Arc: right %3d wrong %2d invalid %2d refused %3d |"
    F="$F Intersection: valid %3d invalid %2d refused %3d | input changed %d%s\n"
    printf "$F" \
        $(basename $f .txt) $(a "wrong 0$") $(a "wrong [1-9]") $(a INVALID) $(a REFUSED) \
        $(b "| valid") $(b INVALID) $(b REFUSED) $(grep -c INPUT-CHANGED $f) \
        "$(grep -q '# done' $f || echo ' NOT FINISHED')"
done
