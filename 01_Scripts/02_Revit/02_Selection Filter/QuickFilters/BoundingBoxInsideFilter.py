# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import *
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument  #type:ignore
doc = uidoc.Document


class BoundingBoxInsideScript:
    @staticmethod
    def Run(doc, uidoc):
        value = UnitUtils.ConvertToInternalUnits(10, UnitTypeId.Meters)  #type:ignore
        point = XYZ(0, 0, 0)
        outline = Outline(point, XYZ(value, value, value))

        boundingBoxInsideFilter = BoundingBoxIsInsideFilter(outline)
        collectorFilter = FilteredElementCollector(doc).WherePasses(boundingBoxInsideFilter).ToElements()

        ids = List[ElementId]([n.Id for n in collectorFilter])
        uidoc.Selection.SetElementIds(ids)
        uidoc.ShowElements(ids)

        print(f"Found {len(collectorFilter)} element(s) fully inside 10m bounding box.")
        return list(collectorFilter)


BoundingBoxInsideScript.Run(doc, uidoc)
