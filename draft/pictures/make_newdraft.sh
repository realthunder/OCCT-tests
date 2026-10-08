#!/bin/bash
# make_newdraft.sh <outdir> -- the pictures of fcad docs/NewDraft.md
# (newdraft.py says what they show).
#
# Each case is drafted both of its ways in FreeCADCmd, one process each, the
# panels rendered in the FreeCAD GUI (the fillet pictures' render.py) and
# laid out. The "before" column of the #876 case needs a Part.so from before
# the cone tool on the face's own cone (fcad d2d1275cb7^): give it as
# PART_BEFORE, and it stands in for the build's own while that column is
# drafted (put back after, its time kept).
#
# env: DRAFT_WORK  scratch directory (default /tmp/draft-pictures)
#      FCBUILD     a FreeCAD build
#      RUN         the wrapper that runs a command in the build's environment
#      PART_BEFORE the Part.so for the "before" column
#      NEWDRAFT_ONLY the cases to make (newdraft.py's names), the rest left
set -e
HERE=$(cd $(dirname $0) && pwd)
OUT=${1:?usage: make_newdraft.sh <outdir>}
export DRAFT_WORK=${DRAFT_WORK:-/tmp/draft-pictures}
RUN=${RUN:-$HOME/works/sw/fcad/.conda/run.sh}
MAC=$([ "$(uname)" = Darwin ] && echo 1 || true)
if [ -n "$MAC" ]; then
    FCBUILD=${FCBUILD:-$HOME/works/sw/fcad/build/mac-relwithdebinfo-801}
else
    FCBUILD=${FCBUILD:-$HOME/works/sw/fcad/build/conda-relwithdebinfo-801}
fi
W=$DRAFT_WORK/newdraft
mkdir -p $W/r $W/home
rm -rf $W/png

cases() { python3 -c "import sys; sys.path.insert(0, '$HERE'); import newdraft; $1"; }
draft() {
    CASE=$1 COL=$2 OUT=$W/r FREECAD_USER_HOME=$W/home \
        $RUN $FCBUILD/bin/FreeCADCmd $HERE/newdraft.py > $W/r/$1.$2.log 2>&1 < /dev/null
    grep -q '^DONE' $W/r/$1.$2.log || { echo "$1 $2 failed, see $W/r/$1.$2.log"; exit 1; }
}
PART=$FCBUILD/Mod/Part/Part.so
for c in $(cases "print(' '.join(newdraft.CASES))"); do
    for col in $(cases "print(' '.join(x[0] for x in newdraft.CASES['$c'][5]))"); do
        if [ "$col" = before ]; then
            [ -n "$PART_BEFORE" ] || { echo "$c: the before column needs PART_BEFORE"; exit 1; }
            cp -p $PART $W/Part.so.own
            cp $PART_BEFORE $PART
            trap "cp -p $W/Part.so.own $PART" EXIT
            draft $c $col
            cp -p $W/Part.so.own $PART
            trap - EXIT
        else
            draft $c $col
        fi
    done
done

$RUN python $HERE/newdraft.py jobs
if [ -n "$MAC" ]; then
    # a .py given to the GUI opens in the editor on macOS; a macro runs
    cp $HERE/../../fillet/pictures/render.py $W/render.FCMacro
    JOBS=$W/jobs.json FREECAD_USER_HOME=$W/home $RUN $FCBUILD/bin/FreeCAD $W/render.FCMacro \
        > $W/render.log 2>&1
else
    JOBS=$W/jobs.json FREECAD_USER_HOME=$W/home xvfb-run -a -s "-screen 0 1600x1200x24" \
        $RUN $FCBUILD/bin/FreeCAD $HERE/../../fillet/pictures/render.py > $W/render.log 2>&1
fi
grep -q '^DONE' $W/render.log || { echo "render failed, see $W/render.log"; exit 1; }
$RUN python $HERE/newdraft.py $OUT
