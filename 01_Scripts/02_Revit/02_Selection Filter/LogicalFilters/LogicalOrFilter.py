# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import *
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument  #type:ignore
doc = uidoc.Document


class LogicalOrFilterScript:
    @staticmethod
    def Run(doc):
        doorsFilter = ElementCategoryFilter(BuiltInCategory.OST_Doors)
        windowsFilter = ElementCategoryFilter(BuiltInCategory.OST_Windows)

        filters = List[ElementFilter]([doorsFilter, windowsFilter])
        logicalFilter = LogicalOrFilter(filters)

        collector = FilteredElementCollector(doc).WherePasses(logicalFilter).ToElements()

        print(f"Found {len(collector)} Door/Window element(s) via LogicalOrFilter.")
        return list(collector)


LogicalOrFilterScript.Run(doc)
