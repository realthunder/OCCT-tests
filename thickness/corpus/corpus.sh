#!/bin/bash
# corpus.sh <tool dir> [env assignment]: the thickness of each face removed at +-1 and
# +-0.5, both joins (j0 Arc, j1 Intersection), and the offset of the whole, over
# #346's revolve, the breps/ shapes, the breps/apex/ ones and #613's (breps/t613.brep);
# 1072 runs. The env assignment picks the libraries, e.g.
#   corpus.sh bin DYLD_LIBRARY_PATH=/tmp/lib        (macOS; LD_LIBRARY_PATH on Linux)
#   corpus.sh bin X=1                               (the tools' own rpath: the install)
# Compare with baseline.txt, timings stripped:
#   diff <(perl -pe 's/ [0-9.]+s$//' baseline.txt) <(perl -pe 's/ [0-9.]+s$//' new.txt)
T=$(cd "${1:?usage: corpus.sh <tool dir> [env assignment]}" && pwd)
E=${2:-X=1}
D=$(cd "$(dirname "$0")" && pwd)
run() { env $1 LC_ALL=C perl -e 'alarm 120; exec @ARGV' "${@:2}" 2>&1 | grep -E "^(done|not done|threw)" | sed 's/ [0-9.]*s / /; s/area [0-9]\{12,\}[0-9.]*/area HUGE/'; }
for b in "$D/../models/issue346_revolve.brep" "$D"/breps/{cside,cslot,g5,g10,chg10,bg10,bslot,t001,i521}.brep "$D"/breps/apex/*.brep "$D/breps/t613.brep"; do n=$(basename "$b" .brep)
  [ -f "$b" ] || { echo "MISSING $b"; continue; }
  nf=$(grep -c "^Fa" "$b")
  for j in 0 1; do for o in 1 -1 0.5 -0.5; do
    echo "$n off $o j$j | $(run "$E" "$T/offs" "$b" $o $j 0)"
    for f in $(seq 1 $nf); do echo "$n thk f$f $o j$j | $(run "$E" "$T/thk" "$b" $o $j 0 $f)"; done
  done; done
done
echo CMP DONE
