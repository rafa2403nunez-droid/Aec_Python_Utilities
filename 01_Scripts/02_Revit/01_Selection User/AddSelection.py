# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")
clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")

from Autodesk.Revit.DB import *
from Autodesk.Revit.Exceptions import OperationCanceledException
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI.Selection import *
from System.Collections.Generic import List
from System.Windows.Forms import *
from System.Drawing import *

uidoc = __revit__.ActiveUIDocument  #type:ignore
doc = uidoc.Document


class WallSelectionFilter(ISelectionFilter):
    def AllowElement(self, element):
        return element.__class__ == Wall

    def AllowReference(self, reference, position):
        return True


class AddSelectionScript:
    @staticmethod
    def Run(uidoc, doc):
        currentSelection = uidoc.Selection.GetElementIds()
        currentReferences = []
        for id in currentSelection:
            element = doc.GetElement(id)
            currentReferences.append(Reference.ParseFromStableRepresentation(doc, element.UniqueId))
        currentReferences = List[Reference](currentReferences)

        references = None
        try:
            references = uidoc.Selection.PickObjects(ObjectType.Element, WallSelectionFilter(), "Select Walls and click Finish:", currentReferences)
        except OperationCanceledException as ex:
            TaskDialog.Show("Revit API", ex.Message)

        if references is not None:
            elements = [doc.GetElement(reference) for reference in references]
            print(f"Selected {len(elements)} wall(s).")
            return elements
        return []


AddSelectionScript.Run(uidoc, doc)
