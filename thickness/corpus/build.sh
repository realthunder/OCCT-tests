#!/bin/bash
# build.sh <occt install prefix> [out dir, default ./bin]: compiles every tools/*.cpp
# against that OCCT (headers in include/opencascade, libraries in lib), with an rpath
# to it. CXX picks the compiler (default c++).
set -e
P=${1:?usage: build.sh <occt prefix> [out dir]}
D=$(cd "$(dirname "$0")" && pwd)
OUT=${2:-$D/bin}
mkdir -p "$OUT"
LIBS="-lTKOffset -lTKFillet -lTKBool -lTKBO -lTKMesh -lTKShHealing -lTKPrim -lTKTopAlgo -lTKBRep
      -lTKGeomAlgo -lTKGeomBase -lTKG3d -lTKG2d -lTKMath -lTKernel"
# On Linux a RUNPATH, which LD_LIBRARY_PATH outranks, so that a staged library
# wins; a DT_RPATH, which conda's linker writes by default, outranks it.
[ "$(uname)" = Linux ] && LIBS="$LIBS -Wl,--enable-new-dtags"
for f in "$D"/tools/*.cpp; do
  n=$(basename "$f" .cpp)
  ${CXX:-c++} -std=c++17 -w -I"$P/include/opencascade" "$f" -o "$OUT/$n" \
    -L"$P/lib" -Wl,-rpath,"$P/lib" $LIBS
done
echo "built $(ls "$D"/tools/*.cpp | wc -l | tr -d ' ') tools in $OUT"
