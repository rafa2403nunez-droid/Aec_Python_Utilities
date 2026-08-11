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
        if element.__class__ == Wall:
            height = UnitUtils.ConvertFromInternalUnits(element.get_Parameter(BuiltInParameter.WALL_USER_HEIGHT_PARAM).AsDouble(), UnitTypeId.Meters)  #type:ignore
            return height < 3
        return False

    def AllowReference(self, reference, position):
        return True


class PickObjectScript:
    @staticmethod
    def Run(uidoc, doc):
        reference = None
        try:
            reference = uidoc.Selection.PickObject(ObjectType.Element, WallSelectionFilter(), "Select a Wall (height < 3m):")
        except OperationCanceledException as ex:
            TaskDialog.Show("Revit API", ex.Message)

        if reference is not None:
            element = doc.GetElement(reference)
            print(f"Selected wall: {element.Id}")
            return element
        return None


PickObjectScript.Run(uidoc, doc)
