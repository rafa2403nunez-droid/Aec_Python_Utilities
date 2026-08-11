# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Structure import TrussType, Truss

doc = __revit__.ActiveUIDocument.Document  #type:ignore


class TrussCreateScript:
    @staticmethod
    def Run(doc):
        grids = (FilteredElementCollector(doc)
                 .OfClass(Grid).WhereElementIsNotElementType().ToElements())

        truss_type_id = (FilteredElementCollector(doc)
                         .OfClass(FamilySymbol)
                         .WherePasses(ElementCategoryFilter(BuiltInCategory.OST_Truss))
                         .FirstElementId())

        if truss_type_id == ElementId.InvalidElementId:
            print("No truss family loaded in project.")
            return

        if not grids:
            print("No grids found in project.")
            return

        t = Transaction(doc, "PyNET - Create Trusses")
        t.Start()
        try:
            trusses = []
            for grid in grids:
                curve = grid.Curve
                plane = SketchPlane.Create(doc, grid.Id)
                truss = Truss.Create(doc, truss_type_id, plane.Id, curve)
                trusses.append(truss)
            t.Commit()
        except:
            t.RollBack()
            raise

        print(f"Created {len(trusses)} trusses from {len(list(grids))} grids.")


TrussCreateScript.Run(doc)
