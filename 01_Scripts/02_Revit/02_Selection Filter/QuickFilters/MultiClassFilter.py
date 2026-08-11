# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr
import System

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import *
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument  #type:ignore
doc = uidoc.Document


class MultiClassFilterScript:
    @staticmethod
    def Run(doc, uidoc):
        classes = List[System.Type]()
        classes.Add(Floor)
        classes.Add(Wall)
        multiClassFilter = ElementMulticlassFilter(classes)
        collectorFilter = FilteredElementCollector(doc).WherePasses(multiClassFilter).WhereElementIsNotElementType().ToElements()

        ids = List[ElementId]([n.Id for n in collectorFilter])
        uidoc.Selection.SetElementIds(ids)
        uidoc.ShowElements(ids)

        print(f"Found {len(collectorFilter)} Floor/Wall element(s).")
        return list(collectorFilter)


MultiClassFilterScript.Run(doc, uidoc)
