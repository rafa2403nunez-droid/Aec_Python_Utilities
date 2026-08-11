# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Structure import StructuralType
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument  #type:ignore
doc = uidoc.Document


class ElementStructuralTypeFilterScript:
    @staticmethod
    def Run(doc, uidoc):
        structuralTypeFilter = ElementStructuralTypeFilter(StructuralType.Column)
        collectorFilter = FilteredElementCollector(doc).WherePasses(structuralTypeFilter).ToElements()

        ids = List[ElementId]([n.Id for n in collectorFilter])
        uidoc.Selection.SetElementIds(ids)
        uidoc.ShowElements(ids)

        print(f"Found {len(collectorFilter)} structural column(s).")
        return list(collectorFilter)


ElementStructuralTypeFilterScript.Run(doc, uidoc)
