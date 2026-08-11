# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr
import math
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Structure import StructuralType

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

# ---------------------------------------------------------------------------
# Configuration — edit these values before running
# ---------------------------------------------------------------------------

RECT_FAMILY_NAME = "Hueco_Suelos"
CIRC_FAMILY_NAME = "Hueco_Suelos_Circular"

FLOOR_ELEMENT_ID = 150954   # Revit element ID of the host floor

# rotation_deg: angle of the MEP element cross-section in XY (from ConnectorManager).
# Use 0.0 for circular holes — rotation has no effect on them.
HOLES = [
    # (type,   x_mm,    y_mm,     rotation_deg, params_mm)
    ("rect",  1344.2,  -668.2,   -55.0, {"Ancho": 700, "Largo": 600, "Alto_Superior": 25, "Alto_Inferior": 387}),
    ("rect", -6933.8, -3016.7,     0.0, {"Ancho": 960, "Largo": 600, "Alto_Superior": 25, "Alto_Inferior": 387}),
    ("circ", -7062.2, -3016.7,     0.0, {"Radio": 135, "Alto_Superior": 25, "Alto_Inferior": 387}),
]

# ---------------------------------------------------------------------------


def mm_to_ft(mm):
    return mm / 304.8


class MepRotationReader:
    @staticmethod
    def GetRotationDeg(document, revit_element_id):
        """Read cross-section rotation of a MEP element via its connector CoordinateSystem."""
        elem = document.GetElement(ElementId(revit_element_id))
        if elem is None:
            return 0.0
        try:
            for conn in elem.ConnectorManager.Connectors:
                bx = conn.CoordinateSystem.BasisX
                return math.degrees(math.atan2(bx.Y, bx.X))
        except:
            pass
        loc = elem.Location
        if isinstance(loc, LocationCurve):
            d = loc.Curve.Direction
            if abs(d.Z) < 0.999:
                return math.degrees(math.atan2(d.Y, d.X))
        return 0.0


class FamilyFinder:
    @staticmethod
    def GetSymbol(document, family_name):
        for f in FilteredElementCollector(document).OfClass(Family).ToElements():
            if f.Name == family_name:
                return document.GetElement(list(f.GetFamilySymbolIds())[0])
        return None

    @staticmethod
    def InspectParameters(document, family_name):
        for f in FilteredElementCollector(document).OfClass(Family).ToElements():
            if f.Name != family_name:
                continue
            family_doc = document.EditFamily(f)
            try:
                return sorted(
                    p.Definition.Name
                    for p in family_doc.FamilyManager.Parameters
                    if p.IsInstance
                )
            finally:
                family_doc.Close(False)
        return []


class HoleCreator:
    @staticmethod
    def Run(document, floor_id, holes, rect_sym, circ_sym):
        floor = document.GetElement(ElementId(floor_id))
        if floor is None:
            print(f"ERROR: Floor element {floor_id} not found.")
            return []

        created = []
        t = Transaction(document, "Create Floor Openings")
        t.Start()
        try:
            for sym in [rect_sym, circ_sym]:
                if sym and not sym.IsActive:
                    sym.Activate()
            document.Regenerate()

            for hole_type, x_mm, y_mm, rotation_deg, params_mm in holes:
                sym = rect_sym if hole_type == "rect" else circ_sym
                if sym is None:
                    print(f"WARNING: Family for type '{hole_type}' not found — skipping ({x_mm}, {y_mm})")
                    continue

                pt = XYZ(mm_to_ft(x_mm), mm_to_ft(y_mm), 0.0)
                inst = document.Create.NewFamilyInstance(pt, sym, floor, StructuralType.NonStructural)

                for param_name, val_mm in params_mm.items():
                    p = inst.LookupParameter(param_name)
                    if p and not p.IsReadOnly:
                        p.Set(mm_to_ft(val_mm))

                if abs(rotation_deg) > 0.01:
                    axis = Line.CreateBound(pt, XYZ(pt.X, pt.Y, pt.Z + 1))
                    ElementTransformUtils.RotateElement(document, inst.Id, axis, math.radians(rotation_deg))

                created.append({"id": str(inst.Id), "type": hole_type, "x_mm": x_mm, "y_mm": y_mm, "rotation_deg": rotation_deg})
                print(f"  Created {hole_type} hole  id={inst.Id}  at ({x_mm}, {y_mm}) mm  rotation={rotation_deg}°")

            t.Commit()
        except Exception as e:
            t.RollBack()
            print(f"ERROR: {e}")
            raise

        return created


class CreateHoleScript:
    @staticmethod
    def Run(document):
        if document.IsFamilyDocument:
            print("ERROR: Active document is a Family (RFA). Switch to a project document first.")
            return

        for family_name in [RECT_FAMILY_NAME, CIRC_FAMILY_NAME]:
            params = FamilyFinder.InspectParameters(document, family_name)
            if params:
                print(f"{family_name} — instance parameters: {', '.join(params)}")
            else:
                print(f"WARNING: Family '{family_name}' not found in document.")

        rect_sym = FamilyFinder.GetSymbol(document, RECT_FAMILY_NAME)
        circ_sym = FamilyFinder.GetSymbol(document, CIRC_FAMILY_NAME)

        print(f"\nPlacing {len(HOLES)} hole(s) on floor {FLOOR_ELEMENT_ID}...")
        created = HoleCreator.Run(document, FLOOR_ELEMENT_ID, HOLES, rect_sym, circ_sym)
        print(f"\nDone — {len(created)} hole(s) created.")


CreateHoleScript.Run(doc)
