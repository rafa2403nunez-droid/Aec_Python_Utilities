# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Structure import WallFoundationType, WallFoundation

doc = __revit__.ActiveUIDocument.Document  #type:ignore


class WallFoundationCreateScript:
    @staticmethod
    def Run(doc):
        walls = (FilteredElementCollector(doc)
                 .OfClass(Wall).WhereElementIsNotElementType().ToElements())

        foundation_type_id = (FilteredElementCollector(doc)
                              .OfClass(WallFoundationType)
                              .FirstElementId())

        if foundation_type_id == ElementId.InvalidElementId:
            print("No wall foundation type found in project.")
            return

        if not walls:
            print("No walls found in project.")
            return

        t = Transaction(doc, "PyNET - Create Wall Foundations")
        t.Start()
        try:
            foundations = []
            for wall in walls:
                try:
                    wf = WallFoundation.Create(doc, foundation_type_id, wall.Id)
                    foundations.append(wf)
                except Exception:
                    pass
            t.Commit()
        except:
            t.RollBack()
            raise

        print(f"Created {len(foundations)} wall foundations from {len(list(walls))} walls.")


WallFoundationCreateScript.Run(doc)
