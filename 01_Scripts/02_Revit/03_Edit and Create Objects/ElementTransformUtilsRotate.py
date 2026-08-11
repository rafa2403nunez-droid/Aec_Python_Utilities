# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

doc = __revit__.ActiveUIDocument.Document  #type:ignore


def GetCentroid(element):
    box = element.get_BoundingBox(None)
    maxPoint = box.Max
    minPoint = box.Min
    return XYZ((maxPoint.X + minPoint.X) / 2, (maxPoint.Y + minPoint.Y) / 2, (maxPoint.Z + minPoint.Z) / 2)


class ElementTransformUtilsRotateScript:
    @staticmethod
    def Run(doc):
        instanceId = FilteredElementCollector(doc).OfClass(FamilyInstance).FirstElementId()
        if instanceId is None or instanceId == ElementId.InvalidElementId:
            print("No family instance found in the document.")
            return

        element = doc.GetElement(instanceId)
        line = Line.CreateUnbound(GetCentroid(element), XYZ.BasisZ)
        angle = UnitUtils.ConvertToInternalUnits(30, UnitTypeId.Degrees)  #type:ignore

        t = Transaction(doc, "Rotate Element")
        t.Start()
        try:
            ElementTransformUtils.RotateElement(doc, instanceId, line, angle)
            t.Commit()
        except:
            t.RollBack()
            raise

        print(f"Element {instanceId} rotated 30 degrees.")


ElementTransformUtilsRotateScript.Run(doc)
