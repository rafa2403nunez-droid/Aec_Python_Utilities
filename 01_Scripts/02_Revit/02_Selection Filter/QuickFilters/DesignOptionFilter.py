# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import *
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument  #type:ignore
doc = uidoc.Document


class DesignOptionFilterScript:
    @staticmethod
    def Run(doc, uidoc):
        option = DesignOption.GetActiveDesignOptionFilterId(doc)
        designOptionFilter = ElementDesignOptionFilter(option)
        collectorFilter = FilteredElementCollector(doc).WherePasses(designOptionFilter).ToElements()

        ids = List[ElementId]([n.Id for n in collectorFilter])
        uidoc.Selection.SetElementIds(ids)
        uidoc.ShowElements(ids)

        print(f"Found {len(collectorFilter)} element(s) in the active design option.")
        return list(collectorFilter)


DesignOptionFilterScript.Run(doc, uidoc)
