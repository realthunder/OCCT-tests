// issue346_offset: #346's Revolve -- a shell, a cone and a dome turned about
// y, the dome's top a dimple 0.9 degrees deep -- offset inward (Part Offset,
// the Arc join), and the same apex crossed. See ../README.md, "#346".
//
// The dome's meridian is an arc whose centre is 1.05 off the axis: it rises
// past its top and comes down to the axis, 0.015 below the flat. The offset
// of a face coming to a point is trimmed where its meridians cross the axis,
// or extended to it where they fall short, and which was told by the sign of
// the offset alone: a cone point is reached outward and crossed inward. At a
// dimple it is the other way round: inward the offset's meridians end 0.03
// short of the axis, and the trim looked for their crossing beyond the end of
// the surface -- none, and StdFail_NotDone ("Unknown OCC exception" in
// FreeCAD). The gap is left open now, and the sphere round the apex closes
// it, as it does outward (BRepOffset_MakeOffset::CorrectConicalFaces), inward
// reversed. And where the apex is crossed -- a peak inward, or a dimple on a
// solid, whose outside is the other side -- the seam trimmed at the apex had
// no range on the face, -2e100 to 2e100: invalid.
//
// Runs (the Arc join, no intersection): the Revolve -2 and -10; the profile
// with its arc centred 1.05 to the other side of the axis (a peak), -2; the
// dimpled profile closed by the axis and a disc into a solid, a thickness -1
// with the disc removed. Valid, to the area or volume of a run whose every
// face was checked at the offset distance from the input's.
//
// Build (macOS, OCCT install prefix O):
//   clang++ -std=c++17 -w -I$O/include/opencascade issue346_offset.cpp \
//     -L$O/lib -Wl,-rpath,$O/lib -lTKOffset -lTKBO -lTKPrim -lTKTopAlgo -lTKBRep \
//     -lTKGeomAlgo -lTKGeomBase -lTKG3d -lTKG2d -lTKMath -lTKernel -o issue346_offset
// Run: ./issue346_offset issue346_revolve.brep [--write <dir>]
//   (exit 0 when every run passes)
//   --write: each result, <dir>/<run>.brep (none when it is refused), and the
//            two profiles made here, <dir>/peak.brep and dimple_solid.brep
#include <BRepBuilderAPI_MakeEdge.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepBuilderAPI_MakeWire.hxx>
#include <BRepCheck_Analyzer.hxx>
#include <BRepGProp.hxx>
#include <BRepOffsetAPI_MakeOffsetShape.hxx>
#include <BRepOffsetAPI_MakeThickSolid.hxx>
#include <BRepPrimAPI_MakeRevol.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <GC_MakeArcOfCircle.hxx>
#include <GProp_GProps.hxx>
#include <Standard_Failure.hxx>
#include <TopExp.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Face.hxx>
#include <TopoDS_Wire.hxx>
#include <gp_Ax1.hxx>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>

// The Revolve's profile with the arc's centre at (cx, -20.08): a line from
// (37.71, 51.19) to (30, 42), the arc on to the axis; with solid, closed by
// the axis and the disc at the top.
static TopoDS_Shape profile(double cx, bool solid)
{
    const double cy = -20.083431642721106;
    gp_Pnt       a(37.713451316238469, 51.192533317427738, 0), b(30, 42, 0);
    const double r = std::hypot(30 - cx, 42 - cy);
    gp_Pnt       t(0, cy + std::sqrt(r * r - cx * cx), 0);
    const double am = 0.5 * (std::atan2(42 - cy, 30 - cx) + std::atan2(t.Y() - cy, -cx));
    gp_Pnt       m(cx + r * std::cos(am), cy + r * std::sin(am), 0);
    BRepBuilderAPI_MakeWire w(BRepBuilderAPI_MakeEdge(a, b).Edge(),
                              BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(b, m, t).Value()).Edge());
    const gp_Ax1 axis(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0));
    if (!solid)
        return BRepPrimAPI_MakeRevol(w.Wire(), axis).Shape();
    gp_Pnt c(0, a.Y(), 0);
    w.Add(BRepBuilderAPI_MakeEdge(t, c).Edge());
    w.Add(BRepBuilderAPI_MakeEdge(c, a).Edge());
    return BRepPrimAPI_MakeRevol(BRepBuilderAPI_MakeFace(w.Wire()).Face(), axis).Shape();
}

int main(int argc, char** argv)
{
    if (argc < 2) {
        printf("usage: %s issue346_revolve.brep [--write <dir>]\n", argv[0]);
        return 2;
    }
    const char*  dir = argc > 3 && !strcmp(argv[2], "--write") ? argv[3] : nullptr;
    TopoDS_Shape revolve;
    BRep_Builder b;
    if (!BRepTools::Read(revolve, argv[1], b)) {
        printf("cannot read %s\n", argv[1]);
        return 2;
    }
    const TopoDS_Shape peak = profile(-1.0500384390052573, false);
    const TopoDS_Shape dsolid = profile(1.0500384390052573, true);
    if (dir) {
        BRepTools::Write(peak, (std::string(dir) + "/peak.brep").c_str());
        BRepTools::Write(dsolid, (std::string(dir) + "/dimple_solid.brep").c_str());
    }
    struct Run {
        const char*         name;
        const TopoDS_Shape* shape;
        double              offset;
        int                 removed;  // 1-based face removed: a thickness; 0: an offset
        double              want;     // the area of an offset shell, a thickness's volume
    } runs[] = {{"revolve_in2", &revolve, -2., 0, 5966.6887},
                {"revolve_in10", &revolve, -10., 0, 7949.8995},
                {"peak_in2", &peak, -2., 0, 5991.6768},
                {"dimple_solid_thick1", &dsolid, -1., 3, 5287.5411}};
    int bad = 0;
    for (const Run& r : runs) {
        std::string  what;
        TopoDS_Shape res;
        try {
            if (r.removed) {
                TopTools_IndexedMapOfShape faces;
                TopExp::MapShapes(*r.shape, TopAbs_FACE, faces);
                NCollection_List<TopoDS_Shape> rm;
                rm.Append(faces(r.removed));
                BRepOffsetAPI_MakeThickSolid m;
                m.MakeThickSolidByJoin(*r.shape, rm, r.offset, 1e-7);
                if (m.IsDone())
                    res = m.Shape();
                else
                    what = "not done";
            } else {
                BRepOffsetAPI_MakeOffsetShape m;
                m.PerformByJoin(*r.shape, r.offset, 1e-7);
                if (m.IsDone())
                    res = m.Shape();
                else
                    what = "not done";
            }
        } catch (Standard_Failure& e) {
            what = std::string("threw ") + e.what();
        }
        bool ok = false;
        if (!res.IsNull()) {
            GProp_GProps g;
            if (r.removed)
                BRepGProp::VolumeProperties(res, g);
            else
                BRepGProp::SurfaceProperties(res, g);
            const bool valid = BRepCheck_Analyzer(res).IsValid();
            char       buf[128];
            snprintf(buf, sizeof(buf), "%s, %s %.4f", valid ? "valid" : "invalid",
                     r.removed ? "volume" : "area", g.Mass());
            what = buf;
            ok = valid && std::fabs(g.Mass() - r.want) <= 1e-3 * r.want;
            if (dir)
                BRepTools::Write(res, (std::string(dir) + "/" + r.name + ".brep").c_str());
        }
        printf("%-20s %+5g: %s%s\n", r.name, r.offset, what.c_str(), ok ? "" : "  FAIL");
        bad += !ok;
    }
    return bad ? 1 : 0;
}
