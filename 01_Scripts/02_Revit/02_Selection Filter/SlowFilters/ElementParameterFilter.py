# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import *

uidoc = __revit__.ActiveUIDocument  #type:ignore
doc = uidoc.Document

PARAMETER_NAME = "parameter_01"
PARAMETER_VALUE = "Revit API"
MIN_AREA_SQM = 10


class ElementParameterFilterScript:
    @staticmethod
    def Run(doc):
        provider = ParameterValueProvider(ElementId(BuiltInParameter.ROOM_AREA))
        evaluator = FilterNumericGreater()
        value = UnitUtils.ConvertToInternalUnits(MIN_AREA_SQM, UnitTypeId.SquareMeters)  #type:ignore
        rule = FilterDoubleRule(provider, evaluator, value, 0.001)
        filterBuiltIn = ElementParameterFilter(rule)
        collectorNativeParameter = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).WherePasses(filterBuiltIn).ToElements()

        iterator = doc.ParameterBindings.ForwardIterator()
        iterator.Reset()
        providerProject = None
        while iterator.MoveNext():
            if iterator.Key.Name == PARAMETER_NAME:
                providerProject = ParameterValueProvider(iterator.Key.Id)
                break

        collectorProjectParameter = []
        if providerProject is not None:
            evaluatorStr = FilterStringEquals()
            ruleStr = FilterStringRule(providerProject, evaluatorStr, PARAMETER_VALUE, True)
            filterProject = ElementParameterFilter(ruleStr)
            collectorProjectParameter = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).WherePasses(filterProject).ToElements()

        print(f"Rooms with area > {MIN_AREA_SQM}sqm: {len(collectorNativeParameter)}")
        print(f"Rooms with {PARAMETER_NAME} = '{PARAMETER_VALUE}': {len(collectorProjectParameter)}")
        return list(collectorNativeParameter), list(collectorProjectParameter)


ElementParameterFilterScript.Run(doc)
