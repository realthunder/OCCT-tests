// fil <brep> <radius> <x y z>...: fillet the edges whose midpoints are nearest
// the given points; print OCCT's view of the failure.
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <BRepFilletAPI_MakeFillet.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepAdaptor_Curve.hxx>
#include <BRepGProp.hxx>
#include <GProp_GProps.hxx>
#include <TopExp.hxx>
#include <TopoDS.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <Standard_Failure.hxx>
#include <cstdio>
#include <string>
#include <Geom_Plane.hxx>
#include <BRep_Tool.hxx>
#include <TopTools_IndexedDataMapOfShapeListOfShape.hxx>
#include <BRepCheck_Result.hxx>
#include <BRepCheck_ListOfStatus.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <Bnd_Box.hxx>
#include <BRepBndLib.hxx>
#include <cstdlib>
int main(int argc, char** argv)
{
    TopoDS_Shape s;
    BRep_Builder b;
    if (!BRepTools::Read(s, argv[1], b)) { printf("read fails\n"); return 1; }
    double r = atof(argv[2]);
    TopTools_IndexedMapOfShape edges;
    TopExp::MapShapes(s, TopAbs_EDGE, edges);
    BRepFilletAPI_MakeFillet mk(s);
    if (std::string(argv[3]) == "pair") {
        // the edges between a plane with normal n1 and one with normal n2 (either sign)
        gp_Dir n1(atof(argv[4]), atof(argv[5]), atof(argv[6])), n2(atof(argv[7]), atof(argv[8]), atof(argv[9]));
        TopTools_IndexedDataMapOfShapeListOfShape ef;
        TopExp::MapShapesAndUniqueAncestors(s, TopAbs_EDGE, TopAbs_FACE, ef);
        auto nrm = [](const TopoDS_Shape& f, gp_Dir& n) {
            Handle(Geom_Plane) p = Handle(Geom_Plane)::DownCast(BRep_Tool::Surface(TopoDS::Face(f)));
            if (p.IsNull()) return false; n = p->Axis().Direction(); return true; };
        for (int k = 1; k <= ef.Extent(); ++k) {
            if (ef(k).Extent() != 2) continue;
            gp_Dir a, b;
            if (!nrm(ef(k).First(), a) || !nrm(ef(k).Last(), b)) continue;
            bool m = (std::abs(a.Dot(n1)) > 0.999 && std::abs(b.Dot(n2)) > 0.999) || (std::abs(a.Dot(n2)) > 0.999 && std::abs(b.Dot(n1)) > 0.999);
            if (m) { printf("edge %d by pair\n", k); mk.Add(r, TopoDS::Edge(ef.FindKey(k))); }
        }
    }
    for (int i = 3; i + 2 < argc && std::string(argv[3]) != "pair"; i += 3) {
        gp_Pnt p(atof(argv[i]), atof(argv[i + 1]), atof(argv[i + 2]));
        int best = 0; double bd = 1e100;
        for (int k = 1; k <= edges.Extent(); ++k) {
            BRepAdaptor_Curve c(TopoDS::Edge(edges(k)));
            double d = c.Value((c.FirstParameter() + c.LastParameter()) / 2).Distance(p);
            if (d < bd) { bd = d; best = k; }
        }
        printf("edge %d (dist %g)\n", best, bd);
        mk.Add(r, TopoDS::Edge(edges(best)));
    }
    try {
        mk.Build();
    } catch (Standard_Failure& e) {
        printf("exception %s: %s\n", "Standard_Failure", e.GetMessageString());
    }
    printf("done %d contours %d faulty contours %d faulty vertices %d computed %d hasresult %d\n",
           mk.IsDone(), mk.NbContours(), mk.NbFaultyContours(), mk.NbFaultyVertices(),
           mk.NbComputedSurfaces(1), mk.HasResult());
    for (int i = 1; i <= mk.NbContours(); ++i) printf(" stripe %d status %d\n", i, (int)mk.StripeStatus(i));
    for (int i = 1; i <= mk.NbFaultyVertices(); ++i) {
        gp_Pnt p = BRep_Tool::Pnt(mk.FaultyVertex(i));
        printf(" faulty vertex %g %g %g\n", p.X(), p.Y(), p.Z());
    }
    if (mk.IsDone()) {
        GProp_GProps g; BRepGProp::VolumeProperties(mk.Shape(), g);
        printf("valid %d volume %.6f\n", BRepCheck_Analyzer(mk.Shape()).IsValid(), g.Mass());
        if (argc > 0 && getenv("OUTB")) BRepTools::Write(mk.Shape(), getenv("OUTB"));
        if (getenv("CHECK")) {
            BRepCheck_Analyzer an(mk.Shape());
            for (TopAbs_ShapeEnum t : {TopAbs_VERTEX, TopAbs_EDGE, TopAbs_WIRE, TopAbs_FACE, TopAbs_SHELL, TopAbs_SOLID}) {
                TopTools_IndexedMapOfShape m; TopExp::MapShapes(mk.Shape(), t, m);
                for (int k = 1; k <= m.Extent(); ++k) {
                    Handle(BRepCheck_Result) res = an.Result(m(k));
                    if (res.IsNull()) continue;
                    for (res->InitContextIterator(); res->MoreShapeInContext(); res->NextShapeInContext())
                        for (auto st : res->StatusOnShape())
                            if (st != BRepCheck_NoError) {
                                Bnd_Box b; BRepBndLib::Add(m(k), b); double x0,y0,z0,x1,y1,z1; b.Get(x0,y0,z0,x1,y1,z1);
                                printf("  bad type %d #%d status %d bb %.2f %.2f %.2f %.2f %.2f %.2f\n", (int)t, k, (int)st, x0,y0,z0,x1,y1,z1);
                            }
                }
            }
        }
    }
    return 0;
}
