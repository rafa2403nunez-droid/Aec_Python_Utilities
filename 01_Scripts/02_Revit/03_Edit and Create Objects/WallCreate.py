# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr
from difflib import SequenceMatcher

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

doc = __revit__.ActiveUIDocument.Document  #type:ignore

FLOOR_LEVEL_PREFIX = "Level_RNM_"
FLOOR_OFFSET_M = 0.0


def ConvertUnits(value, unitName, to_internal=True):
    units = UnitUtils.GetAllUnits()
    unitFilter = None
    for unit in units:
        name = UnitUtils.GetTypeCatalogStringForUnit(unit)
        ratio = SequenceMatcher(a=name, b=unitName.upper()).ratio()
        if ratio > 0.85:
            unitFilter = unit
            break
    if unitFilter is not None:
        if to_internal:
            return UnitUtils.ConvertToInternalUnits(value, unitFilter)
        else:
            return UnitUtils.ConvertFromInternalUnits(value, unitFilter)
    return None


def GenerateLevels(doc, points, prefix):
    levels = []
    currentLevels = FilteredElementCollector(doc).OfClass(Level).WhereElementIsNotElementType().ToElements()
    for point in points:
        updated = False
        for current in currentLevels:
            if current.Elevation == point.Z and prefix in current.Name:
                updated = True
                levels.append(current)
                break
            elif current.Elevation == point.Z and prefix not in current.Name:
                current.Name = prefix + str(points.index(point))
                updated = True
                levels.append(current)
                break
        if not updated:
            level = Level.Create(doc, point.Z)
            level.Name = prefix + str(points.index(point))
            levels.append(level)
    return levels


def GenerateWalls(document, arrays, wallTypeId, levels):
    walls = []
    wallType = document.GetElement(wallTypeId)
    for level, curves in zip(levels, arrays):
        try:
            for curve in curves:
                wall = Wall.Create(document, curve, wallTypeId, level.Id, 1, 0, False, False)
                if levels.index(level) + 1 < len(levels):
                    topLevel = levels[levels.index(level) + 1]
                    wall.LookupParameter("Top Constraint").Set(topLevel.Id)
                walls.append(wall)
        except:
            pass
    return walls


class WallCreateScript:
    @staticmethod
    def Run(doc):
        wallTypeId = FilteredElementCollector(doc).OfClass(WallType).FirstElementId()
        levels = FilteredElementCollector(doc).OfClass(Level).WhereElementIsNotElementType().ToElements()

        if not levels:
            print("No levels found.")
            return

        level = list(levels)[0]
        startPoint = XYZ(0, 0, 0)
        endPoint = XYZ(ConvertUnits(5, "meters"), 0, 0)
        curve = Line.CreateBound(startPoint, endPoint)

        t = Transaction(doc, "Create Wall")
        t.Start()
        try:
            wall = Wall.Create(doc, curve, wallTypeId, level.Id, ConvertUnits(3, "meters"), 0, False, False)
            t.Commit()
        except:
            t.RollBack()
            raise

        print(f"Created wall id={wall.Id} on level '{level.Name}'.")
        return wall


WallCreateScript.Run(doc)
