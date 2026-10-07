#!/bin/bash
# make_corners.sh <outdir> -- the pictures of fcad docs/CornerBlending.md
# (corners.py says what they show).
#
# The fillets run in FreeCADCmd, the panels render in the FreeCAD GUI (the
# fillet pictures' render.py) and are laid out; the task panel's picture is
# a screenshot of the GUI (panel_shot.py). Opens the GUI on the display.
#
# env: CORNER_WORK scratch directory (default /tmp/corner-pictures)
#      FCBUILD     a FreeCAD build linked against the OCCT fork
#      RUN         the wrapper that runs a command in the build's environment
set -e
HERE=$(cd $(dirname $0) && pwd)
DEST=${1:?usage: make_corners.sh <outdir>}
export CORNER_WORK=${CORNER_WORK:-/tmp/corner-pictures}
RUN=${RUN:-$HOME/works/sw/fcad/.conda/run.sh}
MAC=$([ "$(uname)" = Darwin ] && echo 1 || true)
if [ -n "$MAC" ]; then
    FCBUILD=${FCBUILD:-$HOME/works/sw/fcad/build/mac-relwithdebinfo-801}
else
    FCBUILD=${FCBUILD:-$HOME/works/sw/fcad/build/conda-relwithdebinfo-801}
fi
W=$CORNER_WORK
rm -rf $W/r $W/png
mkdir -p $W/r $W/home

OUT=$W/r FREECAD_USER_HOME=$W/home $RUN $FCBUILD/bin/FreeCADCmd $HERE/corners.py \
    > $W/compute.log 2>&1 < /dev/null
grep -q '^DONE' $W/compute.log || { echo "compute failed, see $W/compute.log"; exit 1; }

$RUN python $HERE/corners.py jobs
gui() {  # gui <script> <log> [VAR=value...]
    local script=$1 log=$2
    shift 2
    if [ -n "$MAC" ]; then
        # a .py given to the GUI opens in the editor on macOS; a macro runs
        cp $script $W/$(basename $script .py).FCMacro
        env "$@" FREECAD_USER_HOME=$W/home $RUN $FCBUILD/bin/FreeCAD \
            $W/$(basename $script .py).FCMacro > $log 2>&1
    else
        env "$@" FREECAD_USER_HOME=$W/home xvfb-run -a -s "-screen 0 1600x1200x24" \
            $RUN $FCBUILD/bin/FreeCAD $script > $log 2>&1
    fi
    grep -q '^DONE' $log || { echo "$(basename $script) failed, see $log"; exit 1; }
}
gui $HERE/render.py $W/render.log JOBS=$W/jobs.json
$RUN python $HERE/corners.py $DEST
gui $HERE/panel_shot.py $W/panel.log SHOT=$DEST/task_panel.png
gui $HERE/panel_shot.py $W/panel_depth.log SHOT=$DEST/task_panel_depth.png DEPTH=1
