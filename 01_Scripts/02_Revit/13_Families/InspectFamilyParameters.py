# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document


class FamilyInspector:
    @staticmethod
    def Run(document):
        if document.IsFamilyDocument:
            print("ERROR: Active document is a Family (RFA). Switch to a project document first.")
            return

        families = FilteredElementCollector(document).OfClass(Family).ToElements()
        families_sorted = sorted(families, key=lambda f: f.Name)

        print(f"Families loaded in document: {len(families_sorted)}\n")

        for f in families_sorted:
            instance_params, type_params = FamilyInspector.GetParameters(document, f)
            print(f"--- {f.Name} ---")
            if instance_params:
                print(f"  Instance parameters ({len(instance_params)}):")
                for name in instance_params:
                    print(f"    [I]  {name}")
            if type_params:
                print(f"  Type parameters ({len(type_params)}):")
                for name in type_params:
                    print(f"    [T]  {name}")
            if not instance_params and not type_params:
                print("  (no parameters)")
            print()

    @staticmethod
    def GetParameters(document, family):
        instance_params = []
        type_params = []
        family_doc = document.EditFamily(family)
        try:
            for p in family_doc.FamilyManager.Parameters:
                name = p.Definition.Name
                if p.IsInstance:
                    instance_params.append(name)
                else:
                    type_params.append(name)
        finally:
            family_doc.Close(False)
        return sorted(instance_params), sorted(type_params)


FamilyInspector.Run(doc)
