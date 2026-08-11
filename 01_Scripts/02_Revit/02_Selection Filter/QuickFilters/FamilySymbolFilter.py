# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI.Selection import *

uidoc = __revit__.ActiveUIDocument  #type:ignore
doc = uidoc.Document


class FamilySymbolFilterScript:
    @staticmethod
    def Run(doc, uidoc):
        reference = None
        try:
            reference = uidoc.Selection.PickObject(ObjectType.Element, "Select a Family Instance (loaded family):")
        except:
            TaskDialog.Show("Revit API", "Operation Cancelled")
            return []

        if reference is None:
            print("No reference selected.")
            return []

        element = doc.GetElement(reference)
        if element.__class__ == FamilyInstance:
            familyId = element.Symbol.Family.Id
            familySymbolFilter = FamilySymbolFilter(familyId)
            collector = FilteredElementCollector(doc).WherePasses(familySymbolFilter).ToElements()
            print(f"Found {len(collector)} symbol(s) for family '{element.Symbol.Family.Name}'.")
            return list(collector)
        else:
            print("Selected element is not a Family Instance.")
            return []


FamilySymbolFilterScript.Run(doc, uidoc)
