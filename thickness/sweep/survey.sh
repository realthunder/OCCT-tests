#!/bin/bash
# survey.sh split|order [placed|turned] [shapes...] -- survey.py over the
# shapes given (default: all of them), four at a time; prints each run that
# differs and a summary line a shape.
# env: FCBUILD  a FreeCAD build linked against this OCCT tree
#      RUN      the wrapper that runs a command in the build's environment
#      LIBDIR   OCCT libraries to preload (TKGeomBase, TKTopAlgo, TKBool, TKOffset)
#      SURVEY_HOME  a scratch FREECAD_USER_HOME (default /tmp/thickness-survey-home)
#      THICK_FREEZE, PERM  as survey.py
HERE=$(cd $(dirname $0) && pwd)
RUN=${RUN:-$HOME/works/sw/fcad/.conda/run.sh}
FCBUILD=${FCBUILD:-$HOME/works/sw/fcad/build/conda-relwithdebinfo-801}
H=${SURVEY_HOME:-/tmp/thickness-survey-home}
mkdir -p $H
PRE=""
if [ -n "$LIBDIR" ]; then
    for l in TKGeomBase TKTopAlgo TKBool TKOffset; do
        [ -f $LIBDIR/lib$l.so.8.0.1 ] && PRE="$PRE $LIBDIR/lib$l.so.8.0.1"
    done
fi
fc() { LD_PRELOAD="$PRE" FREECAD_USER_HOME=$H $RUN $FCBUILD/bin/FreeCADCmd $HERE/survey.py 2>&1; }
MODE=$1; shift
PLACE=""
case "$1" in placed|turned) PLACE=$1; shift;; esac
[ $# -eq 0 ] && set -- $(SHAPE=list fc | grep -a "^ball270 ")
T=$(mktemp -d)
for k in "$@"; do
    while [ $(jobs -r | wc -l) -ge 4 ]; do wait -n; done
    ( SHAPE=$k SURVEY=$MODE PLACE=$PLACE fc | grep -a "^BAD\|^SUMMARY\|not the\|not found" > $T/$k.txt ) &
done
wait
cat $T/*.txt | grep -a -v "^SUMMARY"
cat $T/*.txt | grep -a "^SUMMARY"
