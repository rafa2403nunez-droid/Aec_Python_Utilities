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


class ClassFilterScript:
    @staticmethod
    def Run(doc, uidoc):
        classFilter = ElementClassFilter(Wall)
        collectorFilter = FilteredElementCollector(doc).WherePasses(classFilter).WhereElementIsNotElementType().ToElements()

        collectorSimplified = FilteredElementCollector(doc).OfClass(Wall).WhereElementIsNotElementType().ToElements()

        ids = List[ElementId]([n.Id for n in collectorSimplified])
        uidoc.Selection.SetElementIds(ids)
        uidoc.ShowElements(ids)

        print(f"Found {len(collectorFilter)} wall(s) via ClassFilter, {len(collectorSimplified)} via OfClass.")
        return list(collectorFilter), list(collectorSimplified)


ClassFilterScript.Run(doc, uidoc)
