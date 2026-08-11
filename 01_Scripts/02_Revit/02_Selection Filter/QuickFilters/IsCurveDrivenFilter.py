# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import *
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument  #type:ignore
doc = uidoc.Document


class IsCurveDrivenFilterScript:
    @staticmethod
    def Run(doc, uidoc):
        curveDrivenFilter = ElementIsCurveDrivenFilter()
        collectorFilter = FilteredElementCollector(doc).WherePasses(curveDrivenFilter).ToElements()

        ids = List[ElementId]([n.Id for n in collectorFilter])
        uidoc.Selection.SetElementIds(ids)
        uidoc.ShowElements(ids)

        print(f"Found {len(collectorFilter)} curve-driven element(s).")
        return list(collectorFilter)


IsCurveDrivenFilterScript.Run(doc, uidoc)
