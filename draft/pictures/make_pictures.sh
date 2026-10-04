#!/bin/bash
# make_pictures.sh -- regenerate models/pictures (models/Draft.md).
#
# Builds scratch TKOffset libraries with the Draft package's files as of
# upstream and of the fork just before each fix (../../fillet/pictures/
# mkold.sh), drafts every case of cases.py with each and with the fork as
# installed (compute.py, one process per case, the libraries loaded ahead of
# the installed ones), renders the panels in the FreeCAD GUI (the fillet
# pictures' render.py) and lays them out (compose.py). macOS (the real
# display, DYLD_LIBRARY_PATH) and Linux (Xvfb, LD_PRELOAD) alike.
#
# env: DRAFT_WORK  scratch directory (default /tmp/draft-pictures; the
#                  libraries in it are reused when present)
#      FCBUILD     a FreeCAD build linked against this OCCT tree
#      OCCT_BUILD  this OCCT's build tree
#      RUN         the wrapper that runs a command in the build's environment
#      OUTDIR      where the pictures go (default ../models/pictures)
set -e
HERE=$(cd $(dirname $0) && pwd)
FP=$HERE/../../fillet/pictures
O=${OCCT:-$(cd $HERE && git rev-parse --show-superproject-working-tree)}
[ -n "$O" ] || { echo "run from the fork's tests/fork submodule, or set OCCT to the fork's tree"; exit 1; }
export OCCT=$O
export DRAFT_WORK=${DRAFT_WORK:-/tmp/draft-pictures}
export RUN=${RUN:-$HOME/works/sw/fcad/.conda/run.sh}
MAC=$([ "$(uname)" = Darwin ] && echo 1 || true)
if [ -n "$MAC" ]; then
    FCBUILD=${FCBUILD:-$HOME/works/sw/fcad/build/mac-relwithdebinfo-801}
    export OCCT_BUILD=${OCCT_BUILD:-$O/build_conda_rwdi_801}
else
    FCBUILD=${FCBUILD:-$HOME/works/sw/fcad/build/conda-relwithdebinfo-801}
    export OCCT_BUILD=${OCCT_BUILD:-$O/build_conda_relwithdebinfo_801}
fi
W=$DRAFT_WORK
mkdir -p $W/r $W/old $W/home
tables() { python3 -c "import sys; sys.path.insert(0, '$HERE'); import cases; $1"; }

# The libraries: one per commit -- upstream's is d334's "before".
FILES=$(tables "print(' '.join(cases.DRAFT_FILES))")
COMMITS=$(tables "print(' '.join(sorted({cases.UPSTREAM} | {b for b, _ in cases.STAGES.values()})))")
for c in $COMMITS; do
    ls $W/old/$c/lib/libTKOffset.* > /dev/null 2>&1 ||
        TOOLKITS=TKOffset $FP/mkold.sh $c $W/old/$c $FILES > $W/old/$c.log
done

# Run a command with the libraries of <libdir> (or - for the fork as installed).
with_libs() {
    local lib=$1
    shift
    if [ "$lib" = "-" ]; then
        $RUN "$@"
    elif [ -n "$MAC" ]; then
        # SIP strips DYLD_* from /bin/bash, which RUN is: set it inside.
        $RUN env DYLD_LIBRARY_PATH=$lib "$@"
    else
        LD_PRELOAD="$(ls $lib/*.so.8.0.1 | tr '\n' ' ')" $RUN "$@"
    fi
}

# The cases: compute <libdir or -> <outdir> <case...>; a case whose process
# dies is recorded as a crash.
compute() {
    local lib=$1 out=$2 c
    shift 2
    rm -rf $out
    mkdir -p $out
    for c in "$@"; do
        CASE=$c DRAFT_TOOLS=$HERE OUT=$out FREECAD_USER_HOME=$W/home \
            with_libs $lib $FCBUILD/bin/FreeCADCmd $HERE/compute.py > $out/$c.txt 2> $out/$c.err ||
            true
        grep -q '^DONE' $out/$c.txt ||
            echo '{"kind": "crash", "volume": null, "message": "FreeCAD died"}' > $out/$c.json
    done
}
ALL=$(tables "print(' '.join(cases.CASES))")
compute - $W/r/after $ALL
compute $W/old/$(tables "print(cases.UPSTREAM)")/lib $W/r/up $ALL
for st in $(tables "print(' '.join(cases.STAGES))"); do
    compute $W/old/$(tables "print(cases.STAGES['$st'][0])")/lib $W/r/$st \
        $(tables "print(' '.join(n for n, c in cases.CASES.items() if c[0] == '$st'))")
done

# The pictures.
rm -rf $W/png
$RUN python $HERE/compose.py jobs
if [ -n "$MAC" ]; then
    # a .py given to the GUI opens in the editor on macOS; a macro runs
    cp $FP/render.py $W/render.FCMacro
    JOBS=$W/jobs.json FREECAD_USER_HOME=$W/home $RUN $FCBUILD/bin/FreeCAD $W/render.FCMacro \
        > $W/render.log 2>&1
else
    JOBS=$W/jobs.json FREECAD_USER_HOME=$W/home xvfb-run -a -s "-screen 0 1600x1200x24" \
        $RUN $FCBUILD/bin/FreeCAD $FP/render.py > $W/render.log 2>&1
fi
grep -q '^DONE' $W/render.log || { echo "render failed, see $W/render.log"; exit 1; }
$RUN python $HERE/compose.py ${OUTDIR:-$HERE/../models/pictures}
