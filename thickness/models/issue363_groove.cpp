// issue363: a thickness of a cylinder with a groove across its bottom (a
// half cylinder, its axis on the bottom's plane), 1 inward, the Arc join and
// no intersection -- FreeCAD's Thickness as it comes. See ../README.md, #363.
//
// The top removed: the side meets each face of the groove at both ends of
// it, and the bottom in two arcs where its seam splits it -- two faces
// sharing two edges apart. Their offsets were intersected once, for the
// first of the edges, and the piece of the section nearest it was kept; the
// side's offset had nothing to close it at the other end, was cut off at its
// top, and the result was invalid with the inside dropped.
// The bottoms removed, both (the issue's Thickness001) or the one whose arc
// the side's seam splits: each arc of the side on a removed bottom has its
// offset stretched round the whole circle on the side's offset, two of them
// lay on each other there, and the loops were made of the slivers between
// them -- refused, or invalid. Arcs of one circle now share it.
// Runs: the groove of radius 5, of the issue's 10.06, and of 10.06 under a
// chamfered top (the issue's own shape, built here), each to the volume the
// intersection mode, or booleans, give.
//
// Build (macOS, OCCT install prefix O):
//   clang++ -std=c++17 -w -I$O/include/opencascade issue363_groove.cpp \
//     -L$O/lib -Wl,-rpath,$O/lib -lTKOffset -lTKFillet -lTKBO -lTKPrim -lTKTopAlgo -lTKBRep \
//     -lTKGeomAlgo -lTKGeomBase -lTKG3d -lTKG2d -lTKMath -lTKernel -o issue363_groove
// Run: ./issue363_groove [--write <dir>]   (exit 0 when every run passes)
//   --write: each shape, <dir>/<shape>_in.brep, and each run's result,
//   <dir>/<run>.brep (none when it is refused)
#include <BRepAdaptor_Curve.hxx>
#include <BRepAdaptor_Surface.hxx>
#include <BRepAlgoAPI_Cut.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepFilletAPI_MakeChamfer.hxx>
#include <BRepGProp.hxx>
#include <BRepOffsetAPI_MakeThickSolid.hxx>
#include <BRepPrimAPI_MakeCylinder.hxx>
#include <BRepTools.hxx>
#include <GProp_GProps.hxx>
#include <Standard_Failure.hxx>
#include <TopExp.hxx>
#include <TopExp_Explorer.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>

// The issue's cylinder, r 25.807914 h 14 (15 under a chamfer of 1), less a
// cylinder of radius <theR> along y on its bottom's plane.
static TopoDS_Shape grooved(double theR, bool theChamfer)
{
    const double H = 14;
    TopoDS_Shape s = BRepPrimAPI_MakeCylinder(25.807914, H + (theChamfer ? 1 : 0)).Shape();
    if (theChamfer) {
        BRepFilletAPI_MakeChamfer c(s);
        for (TopExp_Explorer x(s, TopAbs_EDGE); x.More(); x.Next()) {
            BRepAdaptor_Curve a(TopoDS::Edge(x.Current()));
            if (a.GetType() == GeomAbs_Circle && a.Value(a.FirstParameter()).Z() > H)
                c.Add(1, TopoDS::Edge(x.Current()));
        }
        s = c.Shape();
    }
    const TopoDS_Shape groove =
        BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(0, -60, 0), gp::DY()), theR, 120).Shape();
    return BRepAlgoAPI_Cut(s, groove).Shape();
}

int main(int argc, char** argv)
{
    const char* dir = argc > 2 && !strcmp(argv[1], "--write") ? argv[2] : nullptr;
    // removed: 0 the top, 1 both bottoms, 2 the bottom the side's seam splits
    struct Run {
        const char* name;
        const char* shape;
        double      r;
        bool        chamfer;
        int         removed;
        double      volume;
    } runs[] = {{"groove5_top", "groove5", 5, false, 0, 4340.4816},
                {"groove10_top", "groove10", 10.062591, false, 0, 4344.8435},
                {"groove10_chamfer_top", "groove10_chamfer", 10.062591, true, 0, 4576.7380},
                {"groove5_seam_bottom", "groove5", 5, false, 2, 5600.6746},
                {"groove10_bottoms", "groove10", 10.062591, false, 1, 5403.7097},
                {"groove10_chamfer_bottoms", "groove10_chamfer", 10.062591, true, 1, 5495.9907}};
    int bad = 0;
    for (const Run& run : runs) {
        const TopoDS_Shape s = grooved(run.r, run.chamfer);
        // the planar faces: the top highest up, the bottoms on z = 0
        TopTools_IndexedMapOfShape faces;
        TopExp::MapShapes(s, TopAbs_FACE, faces);
        NCollection_List<TopoDS_Shape> removed;
        TopoDS_Shape                   top;
        double                         zTop = -1e100;
        for (int i = 1; i <= faces.Extent(); i++) {
            if (BRepAdaptor_Surface(TopoDS::Face(faces(i))).GetType() != GeomAbs_Plane)
                continue;
            GProp_GProps g;
            BRepGProp::SurfaceProperties(faces(i), g);
            if (g.CentreOfMass().Z() > zTop) {
                zTop = g.CentreOfMass().Z();
                top  = faces(i);
            }
            int nEdges = 0;
            for (TopExp_Explorer x(faces(i), TopAbs_EDGE); x.More(); x.Next())
                nEdges++;
            if (std::abs(g.CentreOfMass().Z()) < 1e-6
                && (run.removed == 1 || (run.removed == 2 && nEdges == 3)))
                removed.Append(faces(i));
        }
        if (run.removed == 0)
            removed.Append(top);
        std::string  what;
        bool         ok = false;
        TopoDS_Shape result;
        try {
            BRepOffsetAPI_MakeThickSolid m;
            m.MakeThickSolidByJoin(s, removed, -1., 1e-3, BRepOffset_Skin, false, false,
                                   GeomAbs_Arc);
            if (!m.IsDone()) {
                what = "refused";
            } else {
                result = m.Shape();
                GProp_GProps g;
                BRepGProp::VolumeProperties(result, g);
                const bool valid = BRepCheck_Analyzer(result).IsValid();
                char       buf[128];
                snprintf(buf, sizeof(buf), "%s, volume %.4f (want %.4f)",
                         valid ? "valid" : "invalid", g.Mass(), run.volume);
                what = buf;
                ok   = valid && std::abs(g.Mass() - run.volume) <= 1e-3 * run.volume;
            }
        } catch (Standard_Failure& e) {
            what = std::string("threw ") + e.what();
        }
        printf("%-24s %s %s\n", run.name, ok ? "ok " : "BAD", what.c_str());
        bad += !ok;
        if (dir) {
            BRepTools::Write(s, (std::string(dir) + "/" + run.shape + "_in.brep").c_str());
            if (!result.IsNull())
                BRepTools::Write(result, (std::string(dir) + "/" + run.name + ".brep").c_str());
        }
    }
    printf("%d bad\n", bad);
    return bad != 0;
}
