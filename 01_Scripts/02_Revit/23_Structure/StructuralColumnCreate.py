# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Structure import StructuralType

doc = __revit__.ActiveUIDocument.Document  #type:ignore


def m_to_ft(meters):
    return UnitUtils.ConvertToInternalUnits(meters, UnitTypeId.Meters)


class StructuralColumnCreateScript:
    @staticmethod
    def Run(doc):
        col_symbol = next(
            (fs for fs in FilteredElementCollector(doc).OfClass(FamilySymbol)
             if fs.Category.Id.IntegerValue == int(BuiltInCategory.OST_StructuralColumns)),
            None
        )

        if col_symbol is None:
            print("No structural column family loaded in project.")
            return

        levels = list(FilteredElementCollector(doc)
                      .OfClass(Level).WhereElementIsNotElementType().ToElements())
        levels.sort(key=lambda l: l.Elevation)

        if len(levels) < 2:
            print("Need at least 2 levels to create a structural column.")
            return

        base_level = levels[0]
        top_level = levels[1]
        insertion_point = XYZ(0, 0, base_level.Elevation)

        t = Transaction(doc, "PyNET - Create Structural Column")
        t.Start()
        try:
            if not col_symbol.IsActive:
                col_symbol.Activate()
            column = doc.Create.NewFamilyInstance(
                insertion_point, col_symbol, base_level, StructuralType.Column)
            column.LookupParameter("Top Level").Set(top_level.Id)
            t.Commit()
        except:
            t.RollBack()
            raise

        print(f"Created structural column id={column.Id} from '{base_level.Name}' to '{top_level.Name}'.")


StructuralColumnCreateScript.Run(doc)
