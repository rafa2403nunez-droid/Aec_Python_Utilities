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


class ElementIdSetFilterScript:
    @staticmethod
    def Run(doc, uidoc):
        selection = None
        try:
            selection = uidoc.Selection.PickElementsByRectangle("Select elements with rectangle selection:")
        except:
            TaskDialog.Show("Revit API", "Operation Cancelled")
            return []

        if not selection:
            print("No elements selected.")
            return []

        ids = List[ElementId]([element.Id for element in selection])
        elementIdSetFilter = ElementIdSetFilter(ids)  #type:ignore
        collectorFilter = FilteredElementCollector(doc).WherePasses(elementIdSetFilter).OfClass(Wall).ToElements()

        print(f"Found {len(collectorFilter)} wall(s) from selection via ElementIdSetFilter.")
        return list(collectorFilter)


ElementIdSetFilterScript.Run(doc, uidoc)
