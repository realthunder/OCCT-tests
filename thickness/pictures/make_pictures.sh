#!/bin/bash
# make_pictures.sh -- regenerate models/pictures (README.md, "Pictures").
#
# Builds scratch TKBool/TKOffset libraries for upstream's chain files and for
# the fork just before each fix (mkold.sh), runs every case of cases.py on
# each and on the fork as built (compute.py, the libraries preloaded), renders
# the panels under Xvfb (mkjobs.py, render.py) and lays them out (compose.py).
#
# env: THICK_WORK  scratch directory (default /tmp/thickness-pictures; the
#                  libraries in it are reused when present)
#      FCBUILD     a FreeCAD build linked against this OCCT tree
#      RUN         the wrapper that runs a command in the build's environment
#      OUTDIR      where the pictures go (default ../models/pictures)
#      RENDER_BATCH  panels rendered by one run of the viewer (default 100)
#      RENDER_VMEM   the viewer's address space limit in kB (default 20 GB)
#      ONLY        case names: only these are run and pictured (and only
#                  their stages' libraries made); the other pictures stay
#
# On macOS the libraries are named as the clients load them
# (libTKOffset.8.0.dylib) and put first by DYLD_LIBRARY_PATH, set inside $RUN
# (a protected shell drops DYLD_* from its environment), and the viewer runs
# on the screen, given a macro: a .py given to it opens in the editor.
set -e
HERE=$(cd $(dirname $0) && pwd)
export THICK_WORK=${THICK_WORK:-/tmp/thickness-pictures}
export RUN=${RUN:-$HOME/works/sw/fcad/.conda/run.sh}
if [ "$(uname)" = Darwin ]; then
    MAC=1
    FCBUILD=${FCBUILD:-$HOME/works/sw/fcad/build/mac-relwithdebinfo-801}
else
    MAC=
    FCBUILD=${FCBUILD:-$HOME/works/sw/fcad/build/conda-relwithdebinfo-801}
fi
W=$THICK_WORK
mkdir -p $W/r $W/old $W/home
tables() { python3 -c "import sys; sys.path.insert(0, '$HERE'); import cases; $1"; }
if [ -n "$MAC" ]; then
    LIBS="libTKBool.8.0.dylib libTKOffset.8.0.dylib"
else
    LIBS="libTKBool.so.8.0.1 libTKOffset.so.8.0.1"
fi
OFFLIB=${LIBS#* }

# The libraries: "up" and one per stage.
set -- $(tables "print(cases.UPSTREAM[0], ' '.join(cases.UPSTREAM[1]))")
if [ ! -e $W/old/up/lib/$OFFLIB ]; then
    # upstream's files of the chain's packages, those the fork has changed
    O=${OCCT:-$(cd $HERE && git rev-parse --show-superproject-working-tree)}
    UPFILES=$(cd $O && git diff --name-only $1 HEAD -- "${@:2}")
    $HERE/mkold.sh $1 $W/old/up $UPFILES > $W/old/up.log
fi
if [ -n "$ONLY" ]; then
    STAGES=$(tables "print(' '.join(sorted({cases.CASES[n][0] for n in '$ONLY'.split()})))")
else
    STAGES=$(tables "print(' '.join(cases.STAGES))")
fi
for st in $STAGES; do
    commit=$(tables "print(cases.STAGES['$st'][0])")
    [ -e $W/old/$st/lib/$OFFLIB ] || $HERE/mkold.sh $commit $W/old/$st > $W/old/$st.log
done

# The cases: compute <libdir or -> <outdir> [VAR=value...]
compute() {
    local lib=$1 out=$2 pre=""
    shift 2
    rm -rf $out
    if [ -n "$MAC" ]; then
        [ "$lib" != "-" ] && pre=$lib
        env "$@" THICK_TOOLS=$HERE OUT=$out ONLY="$ONLY" FREECAD_USER_HOME=$W/home \
            $RUN env DYLD_LIBRARY_PATH="$pre" $FCBUILD/bin/FreeCADCmd $HERE/compute.py \
            > $out.txt 2> $out.err
    else
        [ "$lib" != "-" ] && pre=$(for l in $LIBS; do printf '%s ' $lib/$l; done)
        env "$@" THICK_TOOLS=$HERE OUT=$out ONLY="$ONLY" LD_PRELOAD="$pre" FREECAD_USER_HOME=$W/home \
            $RUN $FCBUILD/bin/FreeCADCmd $HERE/compute.py > $out.txt 2> $out.err
    fi
    grep -q '^DONE' $out.txt || { echo "compute $out failed, see $out.err"; exit 1; }
}
compute - $W/r/after STAGES=all
compute $W/old/up/lib $W/r/up STAGES=all
for st in $STAGES; do
    compute $W/old/$st/lib $W/r/$st STAGES=$st
done

# The pictures. The viewer keeps memory for every panel it has drawn
# (render.py), so it is started afresh for each batch, and under a limit on
# its address space: a run that grows anyway is refused memory and fails,
# where without the limit it has taken the machine into swap and down.
rm -rf $W/png
python3 $HERE/mkjobs.py $ONLY
PANELS=$(python3 -c "import json; print(len(json.load(open('$W/jobs.json'))['panels']))")
BATCH=${RENDER_BATCH:-100}
: > $W/render.log
[ -n "$MAC" ] && cp $HERE/render.py $W/render.FCMacro
for ((first = 0; first < PANELS; first += BATCH)); do
    if [ -n "$MAC" ]; then
        (FIRST=$first COUNT=$BATCH JOBS=$W/jobs.json FREECAD_USER_HOME=$W/home \
         $RUN $FCBUILD/bin/FreeCAD $W/render.FCMacro > $W/render.part 2>&1) || true
    else
        (ulimit -v ${RENDER_VMEM:-20000000}
         FIRST=$first COUNT=$BATCH JOBS=$W/jobs.json FREECAD_USER_HOME=$W/home \
             xvfb-run -a -s "-screen 0 1600x1200x24" \
             $RUN $FCBUILD/bin/FreeCAD $HERE/render.py > $W/render.part 2>&1) || true
    fi
    cat $W/render.part >> $W/render.log
    grep -q '^DONE' $W/render.part || { echo "render failed at panel $first, see $W/render.log"; exit 1; }
done
rm -f $W/render.part
$RUN python $HERE/compose.py ${OUTDIR:-$HERE/../models/pictures} $ONLY
