# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

doc = __revit__.ActiveUIDocument.Document  #type:ignore


class ElementTransformUtilsMoveScript:
    @staticmethod
    def Run(doc):
        instanceId = FilteredElementCollector(doc).OfClass(FamilyInstance).FirstElementId()
        if instanceId is None or instanceId == ElementId.InvalidElementId:
            print("No family instance found in the document.")
            return

        t = Transaction(doc, "Move Element")
        t.Start()
        try:
            ElementTransformUtils.MoveElement(doc, instanceId, XYZ(20, 20, 0))
            t.Commit()
        except:
            t.RollBack()
            raise

        print(f"Element {instanceId} moved by (20, 20, 0).")


ElementTransformUtilsMoveScript.Run(doc)
