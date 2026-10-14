// NCollection_ForkState across modules, with clang: the fork's state found from a client through
// dynamic_cast on CommonBaseAllocator(), and the refusals of a frozen shape counted on the thread
// whoever raises them.
//
// 1. The executable: NCollection_ForkState::Get() is not null.
// 2. A refusal raised by the executable's own copy of an inline setter (BRep_TVertex::Tolerance on an
//    Immutable vertex) and one raised in the library (BRep_Builder::UpdateVertex, exported) each add
//    one to TopoDS_LockedShape::Raised() -- as the executable's inline copy reads it and as the C
//    function TopoDS_LockedShape_Raised, looked up by name, reads it.
// 3. The same from a module loaded with dlopen(RTLD_LOCAL): it finds the state and its refusal is
//    counted where the executable reads it -- once with the module built with default visibility,
//    once with hidden (-fvisibility=hidden -fvisibility-inlines-hidden), as FreeCAD's modules may be.
//
//   c++ -std=c++17 -fPIC -dynamiclib (-shared on Linux) -I<inc> forkstate_lib.cpp -o libforkstate_default.<so|dylib> \
//       -L<lib> -lTKernel -lTKMath -lTKBRep -lTKTopAlgo -Wl,-rpath,<lib>
//   (the same with -fvisibility=hidden -fvisibility-inlines-hidden -o libforkstate_hidden.<so|dylib>)
//   c++ -std=c++17 -I<inc> forkstate.cpp -o forkstate -L<lib> -lTKernel -lTKMath -lTKBRep -lTKTopAlgo \
//       -Wl,-rpath,<lib> -ldl
//   ./forkstate ./libforkstate_default.<so|dylib> ./libforkstate_hidden.<so|dylib>
#include <BRepBuilderAPI_MakeVertex.hxx>
#include <BRep_Builder.hxx>
#include <BRep_TVertex.hxx>
#include <NCollection_ForkState.hxx>
#include <TopoDS_LockedShape.hxx>
#include <TopoDS_Vertex.hxx>
#include <gp_Pnt.hxx>

#include <cstdio>
#include <dlfcn.h>

static int fails = 0;
#define CHECK(c)                                                                                   \
  do                                                                                               \
  {                                                                                                \
    if (!(c))                                                                                      \
    {                                                                                              \
      printf("FAIL line %d: %s\n", __LINE__, #c);                                                  \
      fails++;                                                                                     \
    }                                                                                              \
  } while (0)

int main(int argc, char** argv)
{
  typedef unsigned int (*RaisedF)();
  const RaisedF raisedC = (RaisedF)dlsym(RTLD_DEFAULT, "TopoDS_LockedShape_Raised");
  CHECK(raisedC != nullptr);
  CHECK(NCollection_ForkState::Get() != nullptr);
  if (fails)
  {
    printf("FAILED: the fork's state is not found from the executable\n");
    return 1;
  }
  const unsigned int n0 = TopoDS_LockedShape::Raised();
  CHECK(raisedC() == n0);

  // the executable's copy of the inline setter
  const TopoDS_Vertex aV = BRepBuilderAPI_MakeVertex(gp_Pnt(0, 0, 0)).Vertex();
  aV.TShape()->Immutable(true);
  bool isRefused = false;
  try
  {
    occ::down_cast<BRep_TVertex>(aV.TShape())->Tolerance(0.5);
  }
  catch (const TopoDS_LockedShape&)
  {
    isRefused = true;
  }
  CHECK(isRefused);
  CHECK(TopoDS_LockedShape::Raised() == n0 + 1);
  CHECK(raisedC() == n0 + 1);

  // the library's
  isRefused = false;
  try
  {
    BRep_Builder().UpdateVertex(aV, 0.5);
  }
  catch (const TopoDS_LockedShape&)
  {
    isRefused = true;
  }
  CHECK(isRefused);
  CHECK(TopoDS_LockedShape::Raised() == n0 + 2);
  CHECK(raisedC() == n0 + 2);
  printf("executable: state found, refusals counted %u -> %u (inline setter, library)\n", n0,
         TopoDS_LockedShape::Raised());

  // modules loaded with RTLD_LOCAL
  for (int i = 1; i < argc; i++)
  {
    void* aLib = dlopen(argv[i], RTLD_NOW | RTLD_LOCAL);
    CHECK(aLib != nullptr);
    if (aLib == nullptr)
    {
      printf("  %s: %s\n", argv[i], dlerror());
      continue;
    }
    typedef void (*ProbeF)(int*, long*, long*);
    const ProbeF aProbe = (ProbeF)dlsym(aLib, "forkstate_probe");
    CHECK(aProbe != nullptr);
    if (aProbe == nullptr)
    {
      continue;
    }
    const unsigned int nBefore = TopoDS_LockedShape::Raised();
    int                aFound  = 0;
    long               aSeenBefore = 0, aSeenAfter = 0;
    aProbe(&aFound, &aSeenBefore, &aSeenAfter);
    CHECK(aFound == 1);
    CHECK(aSeenBefore == (long)nBefore);
    CHECK(aSeenAfter == (long)nBefore + 1);
    CHECK(TopoDS_LockedShape::Raised() == nBefore + 1);
    CHECK(raisedC() == nBefore + 1);
    printf("%s: state %s, the module saw %ld -> %ld, the executable %u -> %u\n", argv[i],
           aFound ? "found" : "NOT found", aSeenBefore, aSeenAfter, nBefore, TopoDS_LockedShape::Raised());
  }
  printf("%s\n", fails ? "FAILED" : "ok");
  return fails ? 1 : 0;
}
