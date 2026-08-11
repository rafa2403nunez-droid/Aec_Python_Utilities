# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import *
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument  #type:ignore
doc = uidoc.Document


class CategoryFilterScript:
    @staticmethod
    def Run(doc, uidoc):
        categoryFilter = ElementCategoryFilter(BuiltInCategory.OST_Walls)
        collectorFilter = FilteredElementCollector(doc).WherePasses(categoryFilter).WhereElementIsNotElementType().ToElements()

        collectorSimplified = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Walls).WhereElementIsNotElementType().ToElements()

        ids = List[ElementId]()
        for n in collectorSimplified:
            ids.Add(n.Id)
        uidoc.Selection.SetElementIds(ids)
        uidoc.ShowElements(ids)

        print("\n".join([e.Name for e in collectorFilter]))
        print(f"Found {len(collectorFilter)} wall(s) via CategoryFilter, {len(collectorSimplified)} via OfCategory.")
        return list(collectorFilter), list(collectorSimplified)


CategoryFilterScript.Run(doc, uidoc)
