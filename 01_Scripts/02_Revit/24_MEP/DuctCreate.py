# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Mechanical import *

doc = __revit__.ActiveUIDocument.Document  #type:ignore


def m_to_ft(meters):
    return UnitUtils.ConvertToInternalUnits(meters, UnitTypeId.Meters)


class DuctCreateScript:
    @staticmethod
    def Run(doc):
        duct_type_id = (FilteredElementCollector(doc)
                        .OfClass(DuctType).FirstElementId())

        if duct_type_id == ElementId.InvalidElementId:
            print("No duct type found in project.")
            return

        level = (FilteredElementCollector(doc)
                 .OfClass(Level).WhereElementIsNotElementType().FirstElement())

        if level is None:
            print("No level found in project.")
            return

        mep_system = next(
            (s for s in FilteredElementCollector(doc).OfClass(MEPSystemType)
             if s.SystemClassification == MEPSystemClassification.ReturnAir),
            None
        )

        if mep_system is None:
            print("No ReturnAir MEP system type found.")
            return

        start = XYZ(0, 0, m_to_ft(3))
        end = XYZ(m_to_ft(5), 0, m_to_ft(3))

        t = Transaction(doc, "PyNET - Create Duct")
        t.Start()
        try:
            duct = Duct.Create(doc, mep_system.Id, duct_type_id, level.Id, start, end)
            t.Commit()
        except:
            t.RollBack()
            raise

        print(f"Created duct id={duct.Id} on level '{level.Name}'.")


DuctCreateScript.Run(doc)
