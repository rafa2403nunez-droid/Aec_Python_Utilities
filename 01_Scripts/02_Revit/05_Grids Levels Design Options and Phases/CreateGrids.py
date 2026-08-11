# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

doc = __revit__.ActiveUIDocument.Document  #type:ignore

GRID_COUNT = 5
GRID_SPACING_M = 3.0
GRID_LENGTH_M = 12.0


def m_to_ft(meters):
    return UnitUtils.ConvertToInternalUnits(meters, UnitTypeId.Meters)


class CreateGridsScript:
    @staticmethod
    def Run(doc):
        spacing = m_to_ft(GRID_SPACING_M)
        length = m_to_ft(GRID_LENGTH_M)

        t = Transaction(doc, "PyNET - Create Grids")
        t.Start()
        try:
            grids_x, grids_y = [], []

            for i in range(GRID_COUNT):
                offset = i * spacing

                # X-direction grids (vertical lines)
                start = XYZ(offset, 0, 0)
                end = XYZ(offset, length, 0)
                g = Grid.Create(doc, Line.CreateBound(start, end))
                g.Name = f"X-{i + 1}"
                grids_x.append(g)

                # Y-direction grids (horizontal lines)
                start = XYZ(0, offset, 0)
                end = XYZ(length, offset, 0)
                g = Grid.Create(doc, Line.CreateBound(start, end))
                g.Name = f"Y-{i + 1}"
                grids_y.append(g)

            t.Commit()
        except:
            t.RollBack()
            raise

        print(f"Created {len(grids_x)} X grids and {len(grids_y)} Y grids.")


CreateGridsScript.Run(doc)
