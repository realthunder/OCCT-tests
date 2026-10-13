// A thawed copy holds its original, by an allocator on its list of children,
// and lets go of it with itself: no table beside the TShapes and no destructor
// of TopoDS_TShape's in the fork. A wire's TShape is copied, given the wire's
// edges, thawed, given one more, and asked for its original, <n> times over;
// the original's reference count must be back where it started.
//
// The original is asked for through TopoDS_TShape_ThawedFrom, and the lock
// and the count of refusals through their C functions, all looked up by name
// at run time, as FreeCAD binds them. Thaw() itself is the fork's: this is a
// test of the fork's library, not a client that loads with upstream's.
//
//   c++ -std=c++17 -I<include>/opencascade thaw.cpp -L<lib> -lTKernel -lTKMath \
//       -lTKG2d -lTKG3d -lTKGeomBase -lTKBRep -lTKGeomAlgo -lTKTopAlgo -lTKPrim \
//       -Wl,-rpath,<lib> -o thaw
//   ./thaw [n]          (300000 by default)
#include <BRepBuilderAPI_MakeEdge.hxx>
#include <BRepPrimAPI_MakeBox.hxx>
#include <BRep_Builder.hxx>
#include <TopExp_Explorer.hxx>
#include <TopoDS_Iterator.hxx>
#include <TopoDS_TShape.hxx>
#include <gp_Pnt.hxx>

#include <cstdio>
#include <cstdlib>
#ifdef _WIN32
  #include <windows.h>
static void* lookUp(const char* theName)
{
  const HMODULE aLib = GetModuleHandleA("TKBRep.dll");
  return aLib ? (void*)GetProcAddress(aLib, theName) : nullptr;
}
#else
  #include <dlfcn.h>
static void* lookUp(const char* theName)
{
  return dlsym(RTLD_DEFAULT, theName);
}
#endif

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

static int children(const TopoDS_Shape& theS)
{
  int n = 0;
  for (TopoDS_Iterator it(theS); it.More(); it.Next())
  {
    n++;
  }
  return n;
}

int main(int argc, char** argv)
{
  const int n = argc > 1 ? atoi(argv[1]) : 300000;
  typedef void (*ThawedFromF)(const TopoDS_TShape*, occ::handle<TopoDS_TShape>&);
  typedef unsigned int (*RaisedF)();
  typedef void* (*AcquireF)(const TopoDS_TShape*);
  typedef void (*ReleaseF)(void*);
  const ThawedFromF thawedFrom = (ThawedFromF)lookUp("TopoDS_TShape_ThawedFrom");
  const RaisedF     raised     = (RaisedF)lookUp("TopoDS_LockedShape_Raised");
  const AcquireF    acquire    = (AcquireF)lookUp("BRep_RepresentationLock_Acquire");
  const ReleaseF    release    = (ReleaseF)lookUp("BRep_RepresentationLock_Release");
  CHECK(thawedFrom && raised && acquire && release);
  CHECK(lookUp("BinTools_ShapeSet_SetStableBytes") != nullptr);
  CHECK(lookUp("BRepTools_ShapeSet_AddOwnSurfaces") != nullptr);
  if (fails)
  {
    printf("FAILED: a C function of the fork is not there\n");
    return 1;
  }

  const TopoDS_Shape               aBox  = BRepPrimAPI_MakeBox(1, 2, 3).Shape();
  const TopoDS_Shape               aWire = TopExp_Explorer(aBox, TopAbs_WIRE).Current();
  const int                        nw    = children(aWire);
  const occ::handle<TopoDS_TShape> anOrig = aWire.TShape();
  CHECK(nw == 4);
  CHECK(!anOrig->Thawed());
  occ::handle<TopoDS_TShape> aNone;
  thawedFrom(anOrig.get(), aNone);
  CHECK(aNone.IsNull()); // never thawed: no original
  const int aCount0 = anOrig->GetRefCount();
  int       aHeld   = 0;
  for (int k = 0; k < n; k++)
  {
    TopoDS_Shape                     aCopy = aWire.EmptyCopied();
    const occ::handle<TopoDS_TShape> aCT   = aCopy.TShape();
    BRep_Builder                     aB;
    // children first: Thaw() has them to put back under the allocator
    for (TopoDS_Iterator it(aWire); it.More(); it.Next())
    {
      aB.Add(aCopy, it.Value());
    }
    CHECK(children(aCopy) == nw);
    TopoDS_TShape::Thaw(aCT, anOrig);
    CHECK(aCT->Thawed());
    CHECK(children(aCopy) == nw);
    int aSame = 0;
    for (TopoDS_Iterator a(aWire), c(aCopy); a.More() && c.More(); a.Next(), c.Next())
    {
      aSame += a.Value().IsSame(c.Value());
    }
    CHECK(aSame == nw);
    occ::handle<TopoDS_TShape> aGot;
    thawedFrom(aCT.get(), aGot);
    CHECK(aGot == anOrig);
    CHECK(TopoDS_TShape::ThawedFrom(aCT.get()) == anOrig);
    aGot.Nullify();
    if (k == 0)
    {
      aHeld = anOrig->GetRefCount() - aCount0; // the copy holds its original, once
    }
    // and children after the thaw
    aB.Add(aCopy, BRepBuilderAPI_MakeEdge(gp_Pnt(0, 0, 0), gp_Pnt(1, 0, 0)).Edge());
    CHECK(children(aCopy) == nw + 1);
    thawedFrom(aCT.get(), aGot);
    CHECK(aGot == anOrig);
  }
  CHECK(aHeld == 1);
  CHECK(anOrig->GetRefCount() == aCount0); // the copies gone, and their hold with them

  void* aLock = acquire(anOrig.get());
  release(aLock);
  release(nullptr);
  const unsigned int aRaised = raised();
  CHECK(raised() == aRaised);
  printf("%s: %d thaws, the original's count %d as before, refusals raised %u\n",
         fails ? "FAILED" : "ok",
         n,
         (int)anOrig->GetRefCount(),
         aRaised);
  return fails ? 1 : 0;
}
