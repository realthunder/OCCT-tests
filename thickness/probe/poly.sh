#!/bin/bash
# poly.sh <outdir> [shapes...]  -- poly.py for each shape (all when none is named),
# six at a time; then a line a shape: right, wrong, invalid, refused, no reference.
# env: FCBUILD, RUN, LIBN as probe.sh; TS as poly.py
HERE=$(cd $(dirname $0) && pwd)
RUN=${RUN:-$HOME/works/sw/fcad/.conda/run.sh}
FCBUILD=${FCBUILD:-$HOME/works/sw/fcad/build/conda-relwithdebinfo-801}
O=$1; shift
mkdir -p $O/home
[ $# -eq 0 ] && set -- $(python3 -c "import re; print(' '.join(re.findall(r'\"([a-z0-9_]+)\":', open('$HERE/poly.py').read().split('SHAPES = {')[1].split('\n}')[0])))")
PRE=""
for l in TKGeomAlgo TKBool TKOffset; do
    [ -n "$LIBN" ] && PRE="$PRE $LIBN/lib$l.so.8.0.1"
done
export FREECAD_USER_HOME=$O/home MALLOC_ARENA_MAX=8 OPENBLAS_NUM_THREADS=1
for n in "$@"; do
    while [ $(jobs -r | wc -l) -ge 6 ]; do wait -n; done
    ( SHAPE=$n OUT=$O/$n.txt timeout 3000 $RUN env LD_PRELOAD="$PRE" \
        $FCBUILD/bin/FreeCADCmd $HERE/poly.py > $O/$n.log 2>&1 ) &
done
wait
for f in $O/*.txt; do
    c() { grep -c "$1" $f; }
    printf "%-18s runs %3d right %3d WRONG %2d invalid %2d refused %3d no reference %d%s\n" \
        $(basename $f .txt) $(c " | ") $(c "| RIGHT") $(c "| WRONG") $(c INVALID) $(c REFUSED) \
        $(c NOREF) "$(grep -q '# done' $f || echo ' NOT FINISHED')"
done
