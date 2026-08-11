# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import *

uidoc = __revit__.ActiveUIDocument  #type:ignore
doc = uidoc.Document

TOLERANCE_M = 0.3


class GetPanelsOfARoomScript:
    @staticmethod
    def Run(doc):
        rooms = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToElements()
        panels = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_CurtainWallPanels).WhereElementIsNotElementType().ToElements()

        tolerance = UnitUtils.ConvertToInternalUnits(TOLERANCE_M, UnitTypeId.Meters)  #type:ignore

        opts = Options()
        opts.DetailLevel = ViewDetailLevel.Fine

        result = GetPanelsOfARoomScript._GetPanelsOfARoom(list(rooms), list(panels), tolerance, opts)
        print(f"Processed {len(list(rooms))} room(s) and {len(list(panels))} curtain panel(s). Found {len(result)} room-panel group(s).")
        return result

    @staticmethod
    def _GetPanelsOfARoom(rooms, panels, tolerance, opts):
        collectionRoomsPanels = []
        for room in rooms:
            panelsResult = []
            for panel in panels:
                geoElem = panel.get_Geometry(opts)
                for geoObject in geoElem:
                    if not hasattr(geoObject, "GetInstanceGeometry"):
                        continue
                    geoInstances = geoObject.GetInstanceGeometry()
                    for instance in geoInstances:
                        if instance.__class__ == Solid and instance.Volume > 0.1:
                            centroid = instance.ComputeCentroid()
                            p1, p2 = GetPanelsOfARoomScript._GetNormalPoints(panel, centroid, tolerance)
                            if p1 is not None and (room.IsPointInRoom(p1) or room.IsPointInRoom(p2)):
                                if room not in panelsResult:
                                    panelsResult.append(room)
                                panelsResult.append(panel)
            collectionRoomsPanels.append(panelsResult)
        return [x for x in collectionRoomsPanels if x != []]

    @staticmethod
    def _GetNormalPoints(panel, centroid, tolerance):
        h = panel.HandOrientation
        if h.IsAlmostEqualTo(XYZ(1, 0, 0)) or h.IsAlmostEqualTo(XYZ(-1, 0, 0)):
            return XYZ(centroid.X, centroid.Y + tolerance, centroid.Z), XYZ(centroid.X, centroid.Y - tolerance, centroid.Z)
        if h.IsAlmostEqualTo(XYZ(0, 1, 0)) or h.IsAlmostEqualTo(XYZ(0, -1, 0)):
            return XYZ(centroid.X + tolerance, centroid.Y, centroid.Z), XYZ(centroid.X - tolerance, centroid.Y, centroid.Z)
        if h.X < 0 and h.Y > 0:
            return XYZ(centroid.X + tolerance, centroid.Y + tolerance, centroid.Z), XYZ(centroid.X - tolerance, centroid.Y - tolerance, centroid.Z)
        if h.X < 0 and h.Y < 0:
            return XYZ(centroid.X - tolerance, centroid.Y + tolerance, centroid.Z), XYZ(centroid.X + tolerance, centroid.Y - tolerance, centroid.Z)
        if h.X > 0 and h.Y > 0:
            return XYZ(centroid.X + tolerance, centroid.Y - tolerance, centroid.Z), XYZ(centroid.X - tolerance, centroid.Y + tolerance, centroid.Z)
        if h.X > 0 and h.Y < 0:
            return XYZ(centroid.X + tolerance, centroid.Y + tolerance, centroid.Z), XYZ(centroid.X - tolerance, centroid.Y - tolerance, centroid.Z)
        return None, None


GetPanelsOfARoomScript.Run(doc)
