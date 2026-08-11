# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import *

uidoc = __revit__.ActiveUIDocument  #type:ignore
doc = uidoc.Document


class ExclusionFilterScript:
    @staticmethod
    def Run(doc, uidoc):
        activeView = uidoc.ActiveView
        exclusionFilter = ExclusionFilter(activeView.Id)
        collectorFilter = FilteredElementCollector(doc).OfClass(View).WherePasses(exclusionFilter).ToElements()

        print(f"Found {len(collectorFilter)} view(s) excluding the active view.")
        return list(collectorFilter)


ExclusionFilterScript.Run(doc, uidoc)
