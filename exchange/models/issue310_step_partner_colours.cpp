// issue310: face colours written to STEP and read back, on solids whose two
// faces are partners -- one TShape at two places. See ../README.md, #310.
//
// FreeCAD's Part::Cylinder is a prism of the cylinder's bottom face: its top
// is that face moved up, a partner of the bottom. Coloured top red and
// bottom blue (an XCAF document, as FreeCAD's STEP export makes), written
// with the writer's defaults and read back, each end must come back in its
// own colour. Also: the same prism moved by a placement (a location on the
// whole), a cylinder of BRepPrimAPI_MakeCylinder (no partners since 8.0),
// and two partner faces in a compound. A shape with no partners must not
// change at all: that is ../README.md's round trip of the STEP files of the
// trees, not here.
//
// Until ShapeProcess_ShapeContext was fixed here, the writer's DirectFaces
// recorded its history with the faces' locations taken off: the bottom and
// the top were one key, the writer bound one of them, and the top's red was
// written on the bottom, the top left uncoloured -- the prism cases.
//
// Build (macOS, OCCT install prefix O):
//   clang++ -std=c++17 -w -I$O/include/opencascade issue310_step_partner_colours.cpp \
//     -L$O/lib -Wl,-rpath,$O/lib -lTKDESTEP -lTKXCAF -lTKLCAF -lTKCAF -lTKCDF -lTKXSBase \
//     -lTKShHealing -lTKPrim -lTKTopAlgo -lTKBRep -lTKGeomAlgo -lTKGeomBase -lTKG3d -lTKG2d \
//     -lTKMath -lTKernel -lTKService -lTKV3d -o issue310_step_partner_colours
// Run: ./issue310_step_partner_colours <dir>   (exit 0 when every case passes)
//   <dir> gets each case's STEP file, and the shape read back with its face
//   colours (<case>.brep, <case>.colours: a face index from 0 and r g b, as
//   TopExp::MapShapes numbers the faces) for ../pictures/make_pictures.sh.
#include <BRepAdaptor_Surface.hxx>
#include <BRepBuilderAPI_MakeFace.hxx>
#include <BRepGProp.hxx>
#include <BRepPrimAPI_MakeCylinder.hxx>
#include <BRepPrimAPI_MakePrism.hxx>
#include <BRepTools.hxx>
#include <BRep_Builder.hxx>
#include <GProp_GProps.hxx>
#include <Quantity_Color.hxx>
#include <STEPCAFControl_Reader.hxx>
#include <STEPCAFControl_Writer.hxx>
#include <TDF_LabelSequence.hxx>
#include <TDocStd_Document.hxx>
#include <TopExp.hxx>
#include <TopTools_IndexedMapOfShape.hxx>
#include <TopoDS.hxx>
#include <TopoDS_Compound.hxx>
#include <TopoDS_Face.hxx>
#include <XCAFApp_Application.hxx>
#include <XCAFDoc_ColorTool.hxx>
#include <XCAFDoc_DocumentTool.hxx>
#include <XCAFDoc_ShapeTool.hxx>
#include <cstdio>
#include <string>

static double zOf(const TopoDS_Shape& f)
{
    GProp_GProps g;
    BRepGProp::SurfaceProperties(f, g);
    return g.CentreOfMass().Z();
}

static bool isPlane(const TopoDS_Shape& f)
{
    return BRepAdaptor_Surface(TopoDS::Face(f)).GetType() == GeomAbs_Plane;
}

static const Quantity_Color RED(1, 0, 0, Quantity_TOC_RGB), BLUE(0, 0, 1, Quantity_TOC_RGB);

static int bad = 0;

// <shape>'s planar faces: the one above <zMid> red, the others blue; written
// to <dir>/<name>.step, read back, and each planar face's colour checked
static void roundTrip(const char* name, const TopoDS_Shape& shape, double zMid,
                      const std::string& dir)
{
    occ::handle<XCAFApp_Application> app = XCAFApp_Application::GetApplication();
    occ::handle<TDocStd_Document>    doc;
    app->NewDocument("MDTV-XCAF", doc);
    occ::handle<XCAFDoc_ShapeTool> st = XCAFDoc_DocumentTool::ShapeTool(doc->Main());
    occ::handle<XCAFDoc_ColorTool> ct = XCAFDoc_DocumentTool::ColorTool(doc->Main());
    TDF_Label                      label = st->AddShape(shape, false);
    // a located shape is kept as a reference to its prototype, unlocated:
    // the faces are coloured there, z taken where they are placed
    TopoDS_Shape proto = shape;
    if (st->IsReference(label)) {
        st->GetReferredShape(label, label);
        proto = shape.Located(TopLoc_Location());
    }
    TopTools_IndexedMapOfShape faces, placed;
    TopExp::MapShapes(proto, TopAbs_FACE, faces);
    TopExp::MapShapes(shape, TopAbs_FACE, placed);
    bool partners = false;
    for (int i = 1; i <= faces.Extent(); i++) {
        for (int j = i + 1; j <= faces.Extent(); j++)
            partners = partners || faces(i).IsPartner(faces(j));
        if (isPlane(faces(i)))
            ct->SetColor(st->AddSubShape(label, faces(i)), zOf(placed(i)) > zMid ? RED : BLUE,
                         XCAFDoc_ColorSurf);
    }
    const std::string step = dir + "/" + name + ".step";
    STEPCAFControl_Writer w;
    w.SetColorMode(true);
    if (!w.Transfer(doc) || w.Write(step.c_str()) != IFSelect_RetDone) {
        printf("%-16s BAD write failed\n", name);
        bad++;
        return;
    }
    occ::handle<TDocStd_Document> back;
    app->NewDocument("MDTV-XCAF", back);
    STEPCAFControl_Reader r;
    r.SetColorMode(true);
    r.ReadFile(step.c_str());
    r.Transfer(back);
    occ::handle<XCAFDoc_ShapeTool> st2 = XCAFDoc_DocumentTool::ShapeTool(back->Main());
    occ::handle<XCAFDoc_ColorTool> ct2 = XCAFDoc_DocumentTool::ColorTool(back->Main());
    TDF_LabelSequence              roots;
    st2->GetFreeShapes(roots);
    // a placed shape comes back as an assembly of one component: its colours
    // are on the prototype's faces, unlocated, in the same order
    TDF_Label    colourLabel = roots.Value(1);
    TDF_LabelSequence comps;
    if (st2->IsAssembly(colourLabel) && st2->GetComponents(colourLabel, comps) && comps.Length() == 1)
        st2->GetReferredShape(comps.Value(1), colourLabel);
    const TopoDS_Shape         got = st2->GetShape(roots.Value(1));
    TopTools_IndexedMapOfShape gotFaces, colourFaces;
    TopExp::MapShapes(got, TopAbs_FACE, gotFaces);
    TopExp::MapShapes(st2->GetShape(colourLabel), TopAbs_FACE, colourFaces);
    std::string report;
    bool        ok = true;
    FILE*       cols = fopen((dir + "/" + name + ".colours").c_str(), "w");
    for (int i = 1; i <= gotFaces.Extent(); i++) {
        Quantity_Color c;
        const bool     has = ct2->GetColor(colourFaces(i), XCAFDoc_ColorSurf, c);
        if (has && cols)
            fprintf(cols, "%d %g %g %g\n", i - 1, c.Red(), c.Green(), c.Blue());
        if (!isPlane(gotFaces(i)))
            continue;
        const bool  top  = zOf(gotFaces(i)) > zMid;
        const char* want = top ? "red" : "blue";
        const char* is   = !has ? "none" : c.IsEqual(RED) ? "red" : c.IsEqual(BLUE) ? "blue" : "other";
        ok               = ok && std::string(want) == is;
        report += std::string(" ") + (top ? "top " : "bottom ") + is;
    }
    if (cols)
        fclose(cols);
    BRepTools::Write(got, (dir + "/" + name + ".brep").c_str());
    printf("%-16s %s partners %d:%s\n", name, ok ? "ok " : "BAD", partners, report.c_str());
    bad += !ok;
}

int main(int argc, char** argv)
{
    if (argc < 2) {
        printf("usage: %s <dir>\n", argv[0]);
        return 2;
    }
    const std::string dir = argv[1];
    BRepPrimAPI_MakeCylinder cyl(5, 10);
    // FreeCAD's Part::Cylinder: a prism of the bottom face, its top the bottom moved up
    const TopoDS_Shape prism = BRepPrimAPI_MakePrism(cyl.Cylinder().BottomFace(), gp_Vec(0, 0, 10));
    roundTrip("prism", prism, 5, dir);
    gp_Trsf place;
    place.SetRotation(gp::OZ(), 0.5);
    place.SetTranslationPart(gp_Vec(1, 2, 3));
    roundTrip("prism_placed", prism.Moved(TopLoc_Location(place)), 8, dir);
    roundTrip("cylinder", cyl.Shape(), 5, dir);
    // two partner faces in a compound
    const TopoDS_Face bottom = BRepBuilderAPI_MakeFace(gp_Pln(gp::XOY()), 0, 5, 0, 5);
    gp_Trsf           up;
    up.SetTranslation(gp_Vec(0, 0, 10));
    TopoDS_Compound c;
    BRep_Builder    b;
    b.MakeCompound(c);
    b.Add(c, bottom);
    b.Add(c, bottom.Moved(TopLoc_Location(up)));
    roundTrip("faces", c, 5, dir);
    printf("%d bad\n", bad);
    return bad != 0;
}
