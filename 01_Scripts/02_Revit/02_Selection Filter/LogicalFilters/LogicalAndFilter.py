# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import *
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument  #type:ignore
doc = uidoc.Document


class LogicalAndFilterScript:
    @staticmethod
    def Run(doc):
        elementTypeFilter = ElementIsElementTypeFilter()

        categories = List[BuiltInCategory]([BuiltInCategory.OST_Walls, BuiltInCategory.OST_Doors])
        multiCategoryFilter = ElementMulticategoryFilter(categories)

        filters = List[ElementFilter]([multiCategoryFilter, elementTypeFilter])
        logicalFilter = LogicalAndFilter(filters)

        collector = FilteredElementCollector(doc).WherePasses(logicalFilter).ToElements()

        print(f"Found {len(collector)} Wall/Door element type(s) via LogicalAndFilter.")
        return list(collector)


LogicalAndFilterScript.Run(doc)
