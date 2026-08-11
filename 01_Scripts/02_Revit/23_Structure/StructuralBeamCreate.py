# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Structure import StructuralType

doc = __revit__.ActiveUIDocument.Document  #type:ignore


def m_to_ft(meters):
    return UnitUtils.ConvertToInternalUnits(meters, UnitTypeId.Meters)


class StructuralBeamCreateScript:
    @staticmethod
    def Run(doc):
        beam_symbol = next(
            (fs for fs in FilteredElementCollector(doc).OfClass(FamilySymbol)
             if fs.Category.Id.IntegerValue == int(BuiltInCategory.OST_StructuralFraming)),
            None
        )

        if beam_symbol is None:
            print("No structural framing family loaded in project.")
            return

        level = (FilteredElementCollector(doc)
                 .OfClass(Level).WhereElementIsNotElementType().FirstElement())

        if level is None:
            print("No level found in project.")
            return

        start = XYZ(0, 0, level.Elevation)
        end = XYZ(m_to_ft(5), 0, level.Elevation)
        line = Line.CreateBound(start, end)

        t = Transaction(doc, "PyNET - Create Structural Beam")
        t.Start()
        try:
            if not beam_symbol.IsActive:
                beam_symbol.Activate()
            beam = doc.Create.NewFamilyInstance(
                line, beam_symbol, level, StructuralType.Beam)
            t.Commit()
        except:
            t.RollBack()
            raise

        print(f"Created beam id={beam.Id} on level '{level.Name}'.")


StructuralBeamCreateScript.Run(doc)
