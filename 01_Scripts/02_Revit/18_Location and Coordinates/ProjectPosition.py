# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

doc = __revit__.ActiveUIDocument.Document  #type:ignore


def m_to_ft(meters):
    return UnitUtils.ConvertToInternalUnits(meters, UnitTypeId.Meters)


class ProjectPositionScript:
    @staticmethod
    def Run(doc):
        collector = FilteredElementCollector(doc).OfClass(InternalOrigin).ToElements()  # type:ignore
        internal_origin = next((p for p in collector), None)
        if internal_origin is None:
            print("Internal origin not found.")
            return

        internal_point = internal_origin.Position
        project_location = doc.ActiveProjectLocation
        current_pos = project_location.GetProjectPosition(internal_point)

        print(f"Current position: E={current_pos.EastWest:.3f} N={current_pos.NorthSouth:.3f} "
              f"Elev={current_pos.Elevation:.3f} Angle={current_pos.Angle:.4f} rad")

        # Example: set a new project position (60m E, 50m N, 30m elev, 0.5 rad angle)
        new_pos = ProjectPosition(m_to_ft(60), m_to_ft(50), m_to_ft(30), 0.5)

        t = Transaction(doc, "PyNET - Set Project Position")
        t.Start()
        try:
            project_location.SetProjectPosition(internal_point, new_pos)
            t.Commit()
        except:
            t.RollBack()
            raise

        print("Project position updated.")


ProjectPositionScript.Run(doc)
