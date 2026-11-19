#!/bin/bash
# nurbs.sh <outdir>  -- nurbs.py for every shape of shapes.py, shapes2.py and
# shapes3.py, eight at a time; then the count of each verdict.
# env: FCBUILD  a FreeCAD build linked against this OCCT tree
#      RUN      the wrapper that runs a command in the build's environment
#      LIBN     a directory whose TKOffset is preloaded
#      TS, THICK_FIX_LEVEL  as nurbs.py
HERE=$(cd $(dirname $0) && pwd)
RUN=${RUN:-$HOME/works/sw/fcad/.conda/run.sh}
FCBUILD=${FCBUILD:-$HOME/works/sw/fcad/build/conda-relwithdebinfo-801}
O=$1
mkdir -p $O/home
PRE=""
[ -n "$LIBN" ] && PRE="$LIBN/libTKOffset.so.8.0.1"
export FREECAD_USER_HOME=$O/home MALLOC_ARENA_MAX=8 OPENBLAS_NUM_THREADS=1
for m in shapes shapes2 shapes3; do
    for n in $(python3 -c "import re; print(' '.join(re.findall(r'\"([a-z0-9_]+)\":', open('$HERE/$m.py').read().split('SHAPES = {')[1])))"); do
        while [ $(jobs -r | wc -l) -ge 8 ]; do wait -n; done
        ( MOD=$m SHAPE=$n OUT=$O/$m.$n.txt timeout 3000 $RUN env LD_PRELOAD="$PRE" \
            $FCBUILD/bin/FreeCADCmd $HERE/nurbs.py > $O/$m.$n.log 2>&1 ) &
    done
done
wait
cat $O/*.txt | grep -v "^#" | awk -F': ' '{split($2, a, " "); c[a[1]]++} END {for (k in c) printf "%s %d  ", k, c[k]; print ""}'
for f in $O/*.txt; do grep -q '# done' $f || echo "$(basename $f .txt) NOT FINISHED"; done
