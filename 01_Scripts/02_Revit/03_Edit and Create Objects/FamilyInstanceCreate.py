# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Structure import StructuralType

doc = __revit__.ActiveUIDocument.Document  #type:ignore

FAMILY_NAME = "M_Desk"
SYMBOL_NAME = "1525 x 762mm"


class FamilyInstanceCreateScript:
    @staticmethod
    def Run(doc):
        familySymbols = FilteredElementCollector(doc).OfClass(FamilySymbol).ToElements()
        familySymbol = None
        for symbol in familySymbols:
            if symbol.Family.Name == FAMILY_NAME and Element.Name.__get__(symbol) == SYMBOL_NAME:
                familySymbol = symbol
                break

        if familySymbol is None:
            print(f"Family symbol '{FAMILY_NAME} - {SYMBOL_NAME}' not found.")
            return None

        t = Transaction(doc, "Create Family Instance")
        t.Start()
        try:
            if not familySymbol.IsActive:
                familySymbol.Activate()
            instance = doc.Create.NewFamilyInstance(XYZ.Zero, familySymbol, StructuralType.NonStructural)
            t.Commit()
        except:
            t.RollBack()
            raise

        print(f"Created family instance '{FAMILY_NAME}' id={instance.Id} at origin.")
        return instance


FamilyInstanceCreateScript.Run(doc)
