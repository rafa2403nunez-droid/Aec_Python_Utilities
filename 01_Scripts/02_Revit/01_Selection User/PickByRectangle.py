# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import *
from Autodesk.Revit.Exceptions import OperationCanceledException
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI.Selection import *

uidoc = __revit__.ActiveUIDocument  #type:ignore
doc = uidoc.Document


class WallSelectionFilter(ISelectionFilter):
    def AllowElement(self, element):
        return element.__class__ == Wall

    def AllowReference(self, reference, position):
        return True


class PickByRectangleScript:
    @staticmethod
    def Run(uidoc):
        elements = None
        try:
            elements = uidoc.Selection.PickElementsByRectangle(WallSelectionFilter(), "Select Walls with rectangle selection:")
        except OperationCanceledException as ex:
            TaskDialog.Show("Revit API", ex.Message)

        if elements:
            print(f"Selected {len(elements)} wall(s) by rectangle.")
            return list(elements)
        return []


PickByRectangleScript.Run(uidoc)
