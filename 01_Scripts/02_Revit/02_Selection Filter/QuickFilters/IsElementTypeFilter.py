# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import *

uidoc = __revit__.ActiveUIDocument  #type:ignore
doc = uidoc.Document


class IsElementTypeFilterScript:
    @staticmethod
    def Run(doc):
        isElementTypeFilter = ElementIsElementTypeFilter()
        collectorFilter = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Walls).WherePasses(isElementTypeFilter).ToElements()

        collectorSimplified = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Walls).WhereElementIsElementType().ToElements()
        collectorSimplifiedInverse = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Walls).WhereElementIsNotElementType().ToElements()

        print(f"Wall types via filter: {len(collectorFilter)}, via WhereElementIsElementType: {len(collectorSimplified)}, instances: {len(collectorSimplifiedInverse)}.")
        return list(collectorFilter), list(collectorSimplified)


IsElementTypeFilterScript.Run(doc)
