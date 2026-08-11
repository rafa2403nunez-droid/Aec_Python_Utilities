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


class UndoElementRotationScript:
    @staticmethod
    def Run(doc):
        collector = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Planting).WhereElementIsNotElementType().ToElements()
        elements = list(collector)

        initialRotation = [UnitUtils.ConvertFromInternalUnits(element.Location.Rotation, UnitTypeId.Degrees) for element in elements]  #type:ignore

        t = Transaction(doc, "Undo Rotation")
        t.Start()
        try:
            for element in elements:
                rotation = element.Location.Rotation
                origin = GetCentroid(element)
                line = Line.CreateUnbound(origin, XYZ.BasisZ)
                ElementTransformUtils.RotateElement(doc, element.Id, line, -rotation)
            t.Commit()
        except:
            t.RollBack()
            raise

        checkRotation = [UnitUtils.ConvertFromInternalUnits(element.Location.Rotation, UnitTypeId.Degrees) for element in elements]  #type:ignore

        print(f"Undid rotation on {len(elements)} planting element(s).")
        print(f"Initial rotations: {initialRotation}")
        print(f"Final rotations:   {checkRotation}")
        return initialRotation, checkRotation


UndoElementRotationScript.Run(doc)
