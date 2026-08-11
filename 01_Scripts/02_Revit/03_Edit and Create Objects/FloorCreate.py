# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

doc = __revit__.ActiveUIDocument.Document  #type:ignore


def GetRoomPerimeter(room, opts, use_curve_array=True):
    geometries = room.get_Geometry(opts)
    loop = None
    arrayList = None
    for geometry in geometries:
        if geometry.__class__ is Solid and geometry.Volume > 0:
            faces = geometry.Faces
            for face in faces:
                if face.FaceNormal.IsAlmostEqualTo(XYZ.Negate(XYZ.BasisZ)):
                    loop = face.GetEdgesAsCurveLoops()
                    arrayList = face.EdgeLoops
    if use_curve_array and arrayList is not None:
        curveArray = CurveArray()
        for array in arrayList:
            for line in array:
                curveArray.Append(line.AsCurve())
        return curveArray
    return loop


class FloorCreateScript:
    @staticmethod
    def Run(doc):
        rooms = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToElements()
        floorTypeId = FilteredElementCollector(doc).OfClass(FloorType).FirstElementId()

        opts = Options()
        opts.DetailLevel = ViewDetailLevel.Fine

        t = Transaction(doc, "Create Floors")
        t.Start()
        try:
            floors = []
            for room in rooms:
                array = GetRoomPerimeter(room, opts)
                if array is not None:
                    floor = doc.Create.NewFloor(array, doc.GetElement(floorTypeId), room.Level, False)
                    floors.append(floor)
            t.Commit()
        except:
            t.RollBack()
            raise

        print(f"Created {len(floors)} floor(s) from {len(list(rooms))} room(s).")
        return floors


FloorCreateScript.Run(doc)
