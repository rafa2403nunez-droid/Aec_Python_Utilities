# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

doc = __revit__.ActiveUIDocument.Document  #type:ignore


class UnitsDemo:
    @staticmethod
    def Run():
        value = 32.0

        # Revit 2022+ API (UnitTypeId)
        try:
            to_internal = UnitUtils.ConvertToInternalUnits(value, UnitTypeId.Meters)
            from_internal = UnitUtils.ConvertFromInternalUnits(value, UnitTypeId.Meters)
            print(f"{value} m → internal: {to_internal:.6f} ft")
            print(f"{value} internal ft → m: {from_internal:.6f} m")
        except Exception as e:
            print(f"UnitTypeId API not available: {e}")

        # Revit 2021 and earlier fallback (DisplayUnitType — deprecated)
        try:
            to_internal_legacy = UnitUtils.ConvertToInternalUnits(value, DisplayUnitType.DUT_METERS)  # type:ignore
            print(f"Legacy: {value} m → internal: {to_internal_legacy:.6f} ft")
        except Exception:
            print("Legacy DisplayUnitType API not available in this Revit version.")


UnitsDemo.Run()
