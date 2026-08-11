# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import *
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument  #type:ignore
doc = uidoc.Document


class ElementOwnerViewScript:
    @staticmethod
    def Run(doc, uidoc):
        elementOwnerViewFilter = ElementOwnerViewFilter(uidoc.ActiveView.Id)
        collectorFilter = FilteredElementCollector(doc).WherePasses(elementOwnerViewFilter).ToElements()

        ids = List[ElementId]([n.Id for n in collectorFilter])
        uidoc.Selection.SetElementIds(ids)
        uidoc.ShowElements(ids)

        print(f"Found {len(collectorFilter)} element(s) owned by the active view.")
        return list(collectorFilter)


ElementOwnerViewScript.Run(doc, uidoc)
