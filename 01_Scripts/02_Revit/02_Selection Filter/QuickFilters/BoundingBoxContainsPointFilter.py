# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument  #type:ignore
doc = uidoc.Document


class BoundingBoxContainsPointScript:
    @staticmethod
    def Run(doc, uidoc):
        point = XYZ(0, 0, 0)

        boundingBoxFilter = BoundingBoxContainsPointFilter(point)
        collectorFilter = FilteredElementCollector(doc).WherePasses(boundingBoxFilter).ToElements()

        ids = List[ElementId]([n.Id for n in collectorFilter])
        uidoc.Selection.SetElementIds(ids)
        uidoc.ShowElements(ids)

        print(f"Found {len(collectorFilter)} element(s) whose bounding box contains point {point}.")
        return list(collectorFilter)


BoundingBoxContainsPointScript.Run(doc, uidoc)
