# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Electrical import *

doc = __revit__.ActiveUIDocument.Document  #type:ignore


class ElectricalWireCreateScript:
    @staticmethod
    def Run(doc):
        if doc.ActiveView.__class__ != ViewPlan:
            print("Active view is not a floor plan. Wires require a plan view.")
            return

        electrical_systems = (FilteredElementCollector(doc)
                               .OfClass(ElectricalSystem).ToElements())

        if not electrical_systems:
            print("No electrical systems found in project.")
            return

        t = Transaction(doc, "PyNET - Create Wires")
        t.Start()
        try:
            created = 0
            for system in electrical_systems:
                try:
                    system.NewWires(doc.ActiveView, WiringType.Arc)
                    created += 1
                except Exception:
                    pass
            t.Commit()
        except:
            t.RollBack()
            raise

        print(f"Created wires for {created}/{len(list(electrical_systems))} electrical systems.")


ElectricalWireCreateScript.Run(doc)
