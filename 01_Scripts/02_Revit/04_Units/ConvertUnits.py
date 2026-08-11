# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr
from difflib import SequenceMatcher

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

doc = __revit__.ActiveUIDocument.Document  #type:ignore


def convert_units(value, unit_name, to_internal=True):
    """Find a unit type by fuzzy name match and convert value to/from internal Revit units."""
    unit_filter = None
    for unit in UnitUtils.GetAllUnits():
        name = UnitUtils.GetTypeCatalogStringForUnit(unit)
        if SequenceMatcher(a=name, b=unit_name.upper()).ratio() > 0.85:
            unit_filter = unit
            break
    if unit_filter is None:
        return None
    if to_internal:
        return UnitUtils.ConvertToInternalUnits(value, unit_filter)
    return UnitUtils.ConvertFromInternalUnits(value, unit_filter)


class ConvertUnitsScript:
    @staticmethod
    def Run():
        examples = [
            (3.0, "meters", True),
            (10.0, "feet", True),
            (1.0, "inches", False),
        ]
        for value, unit, to_internal in examples:
            result = convert_units(value, unit, to_internal)
            direction = "→ internal" if to_internal else "← from internal"
            print(f"{value} {unit} {direction} = {result:.6f}")


ConvertUnitsScript.Run()
