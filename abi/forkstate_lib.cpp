// The library half of forkstate.cpp: a client module of its own, loaded by the driver with dlopen and
// RTLD_LOCAL, that asks for the fork's state and raises a refusal through its own copy of an inline
// setter. Built twice by the driver's instructions, with default and with hidden visibility.
#include <BRepBuilderAPI_MakeVertex.hxx>
#include <BRep_TVertex.hxx>
#include <NCollection_ForkState.hxx>
#include <TopoDS_LockedShape.hxx>
#include <TopoDS_Vertex.hxx>
#include <gp_Pnt.hxx>

// what the module sees: the fork's state found (1) or not (0), and the count of refusals on this
// thread before and after one raised here (-1 where the refusal was not raised)
extern "C" __attribute__((visibility("default"))) void forkstate_probe(int* theFound,
                                                                      long* theBefore,
                                                                      long* theAfter)
{
  *theFound  = NCollection_ForkState::Get() != nullptr;
  *theBefore = (long)TopoDS_LockedShape::Raised();
  *theAfter  = -1;
  const TopoDS_Vertex aV = BRepBuilderAPI_MakeVertex(gp_Pnt(1, 2, 3)).Vertex();
  aV.TShape()->Immutable(true);
  try
  {
    occ::down_cast<BRep_TVertex>(aV.TShape())->Tolerance(0.5); // inline: this module's copy
  }
  catch (const TopoDS_LockedShape&)
  {
    *theAfter = (long)TopoDS_LockedShape::Raised();
  }
}
