# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

doc = __revit__.ActiveUIDocument.Document  #type:ignore


class WallEditProfileScript:
    @staticmethod
    def Run(doc):
        walls = FilteredElementCollector(doc).OfClass(Wall).WhereElementIsNotElementType().ToElements()
        walls_with_profile = [w for w in walls if w.IsProfileSketchDriven]

        if not walls_with_profile:
            print("No walls with edited profiles found.")
            return

        t = Transaction(doc, "Remove Wall Profiles")
        t.Start()
        try:
            removed = 0
            for wall in walls_with_profile:
                try:
                    wall.RemoveProfileSketch()
                    removed += 1
                except Exception:
                    pass
            t.Commit()
        except:
            t.RollBack()
            raise

        print(f"Removed profile edits from {removed}/{len(walls_with_profile)} walls.")


WallEditProfileScript.Run(doc)
