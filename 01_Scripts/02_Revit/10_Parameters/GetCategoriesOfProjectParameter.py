# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

doc = __revit__.ActiveUIDocument.Document  #type:ignore

TARGET_PARAM_NAME = "ExportParam"


class GetCategoriesOfProjectParameterScript:
    @staticmethod
    def Run(doc, param_name):
        bindings = doc.ParameterBindings
        iterator = bindings.ForwardIterator()

        while iterator.MoveNext():
            if iterator.Key.Name == param_name:
                element_binding = bindings.get_Item(iterator.Key)
                categories = element_binding.Categories
                names = sorted([cat.Name for cat in categories])
                print(f"Parameter '{param_name}' is bound to {len(names)} categories:")
                for name in names:
                    print(f"  {name}")
                return names

        print(f"Parameter '{param_name}' not found in project parameters.")
        return []


GetCategoriesOfProjectParameterScript.Run(doc, TARGET_PARAM_NAME)
