# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

doc = __revit__.ActiveUIDocument.Document  #type:ignore

LEVEL_COUNT = 5
FLOOR_HEIGHT_M = 3.0
BASE_ELEVATION_M = 0.0
LEVEL_PREFIX = "Level_RNM_"


def m_to_ft(meters):
    return UnitUtils.ConvertToInternalUnits(meters, UnitTypeId.Meters)


class CreateLevelsScript:
    @staticmethod
    def Run(doc):
        t = Transaction(doc, "PyNET - Create Levels")
        t.Start()
        try:
            levels = []
            for i in range(LEVEL_COUNT):
                elevation = m_to_ft(BASE_ELEVATION_M + i * FLOOR_HEIGHT_M)
                level = Level.Create(doc, elevation)
                level.Name = f"{LEVEL_PREFIX}{i}"
                levels.append(level)
            t.Commit()
        except:
            t.RollBack()
            raise

        print(f"Created {len(levels)} levels with prefix '{LEVEL_PREFIX}'.")
        for lvl in levels:
            elev_m = UnitUtils.ConvertFromInternalUnits(lvl.Elevation, UnitTypeId.Meters)
            print(f"  {lvl.Name}: {elev_m:.2f} m")


CreateLevelsScript.Run(doc)
