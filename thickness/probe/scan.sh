#!/bin/bash
# scan.sh <outdir> [shapes...]  -- scan.py for each shape (all of shapes.py,
# or of shapes2.py or shapes3.py with SET=2 or 3, when none is named), six at
# a time; then
# islands.py on what they wrote.
# env: FCBUILD, RUN, LIBN as probe.sh; STEP, COUNT, JOIN, TOL, SET as scan.py
HERE=$(cd $(dirname $0) && pwd)
RUN=${RUN:-$HOME/works/sw/fcad/.conda/run.sh}
FCBUILD=${FCBUILD:-$HOME/works/sw/fcad/build/conda-relwithdebinfo-801}
O=$1; shift
mkdir -p $O/home
SHAPESFILE=$HERE/shapes.py; [ "$SET" = 2 ] && SHAPESFILE=$HERE/shapes2.py
[ "$SET" = 3 ] && SHAPESFILE=$HERE/shapes3.py
NAMES="import re; t = open('$SHAPESFILE').read().split('SHAPES = {')[1]"
NAMES="$NAMES; print(' '.join(re.findall(r'\"([a-z0-9_]+)\":', t)))"
[ $# -eq 0 ] && set -- $(python3 -c "$NAMES")
PRE=""
for l in TKGeomAlgo TKBool TKOffset; do
    [ -n "$LIBN" ] && PRE="$PRE $LIBN/lib$l.so.8.0.1"
done
export FREECAD_USER_HOME=$O/home MALLOC_ARENA_MAX=8 OPENBLAS_NUM_THREADS=1
for n in "$@"; do
    while [ $(jobs -r | wc -l) -ge 6 ]; do wait -n; done
    ( SHAPE=$n OUT=$O/$n.txt timeout 6000 $RUN env LD_PRELOAD="$PRE" \
        $FCBUILD/bin/FreeCADCmd $HERE/scan.py > $O/$n.log 2>&1 ) &
done
wait
python3 $HERE/islands.py $O
