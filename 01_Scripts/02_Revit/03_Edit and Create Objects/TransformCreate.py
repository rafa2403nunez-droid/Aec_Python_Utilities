# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

doc = __revit__.ActiveUIDocument.Document  #type:ignore


class TransformCreateScript:
    @staticmethod
    def Run():
        angle = UnitUtils.ConvertToInternalUnits(5, UnitTypeId.Degrees)  #type:ignore

        point = XYZ(3, 3, 6)
        plane = Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ.Zero)

        rotate = Transform.CreateRotationAtPoint(XYZ.BasisZ, angle, XYZ.Zero)
        reflection = Transform.CreateReflection(plane)

        rotatedPoint = rotate.OfPoint(point)
        reflectedPoint = reflection.OfPoint(point)

        print(f"Original: {point}")
        print(f"Rotated 5 deg around Z at origin: {rotatedPoint}")
        print(f"Reflected over XY plane: {reflectedPoint}")
        return rotatedPoint, reflectedPoint


TransformCreateScript.Run()
