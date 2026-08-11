# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import *
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument  #type:ignore
doc = uidoc.Document


class MultiCategoryFilterScript:
    @staticmethod
    def Run(doc, uidoc):
        categories = List[BuiltInCategory]([BuiltInCategory.OST_Walls, BuiltInCategory.OST_Doors])
        multicategoryFilter = ElementMulticategoryFilter(categories)
        collectorFilter = FilteredElementCollector(doc).WherePasses(multicategoryFilter).WhereElementIsNotElementType().ToElements()

        ids = List[ElementId]([n.Id for n in collectorFilter])
        uidoc.Selection.SetElementIds(ids)
        uidoc.ShowElements(ids)

        print(f"Found {len(collectorFilter)} element(s) in Walls + Doors categories.")
        return list(collectorFilter)


MultiCategoryFilterScript.Run(doc, uidoc)
