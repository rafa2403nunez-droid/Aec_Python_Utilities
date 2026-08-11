# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr
import pandas as pd
from pathlib import Path

clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import Application

from System import Environment

doc = Application.ActiveDocument


class WallAnalyzer:
    """
    Iterates all model items, identifies walls by category,
    and aggregates linear meters grouped by wall type.
    """

    @staticmethod
    def Run(document):
        print("Scanning model for walls...")
        walls = {}
        allItems = document.Models.CreateCollectionFromRootItems()

        for modelItem in ModelIterator.IterateAll(allItems):
            category = PropertyReader.GetProperty(modelItem, "Other", "Category")
            if category and ("wall" in category.lower() or "muro" in category.lower()):
                wallType = PropertyReader.GetProperty(modelItem, "Other", "Family and Type") or \
                           PropertyReader.GetProperty(modelItem, "MDE_01_Generales", "MDE_Tipo") or \
                           "Unknown"
                length = PropertyReader.GetLength(modelItem)

                if wallType not in walls:
                    walls[wallType] = {"count": 0, "totalLength": 0.0}
                walls[wallType]["count"] += 1
                if length is not None:
                    walls[wallType]["totalLength"] += length

        result = []
        for wType, data in sorted(walls.items(), key=lambda x: x[1]["totalLength"], reverse=True):
            result.append({
                "Tipo de Muro": wType,
                "Cantidad": data["count"],
                "Metros Lineales (m)": round(data["totalLength"], 2)
            })

        print(f"Found {len(result)} wall types")
        return result


class ModelIterator:
    """
    Utility to traverse the full Navisworks model tree using a stack-based approach.
    """

    @staticmethod
    def IterateAll(items):
        stack = list(items)
        while stack:
            item = stack.pop()
            yield item
            try:
                children = list(item.Children)
                stack.extend(children)
            except:
                pass


class PropertyReader:
    """
    Reads properties from Navisworks model items by category and property name.
    Handles DoubleLength, Double and DisplayString value types.
    """

    @staticmethod
    def GetProperty(item, categoryName, propertyName):
        for cat in item.PropertyCategories:
            if cat.DisplayName == categoryName:
                for prop in cat.Properties:
                    if prop.DisplayName == propertyName:
                        val = prop.Value
                        if val.IsDisplayString:
                            return val.ToDisplayString()
                        elif val.IsDouble:
                            return str(val.ToDouble())
                        elif val.IsDoubleLength:
                            return str(val.ToDoubleLength())
        return None

    @staticmethod
    def GetLength(item):
        for cat in item.PropertyCategories:
            if cat.DisplayName in ("Dimensions", "BaseQuantities"):
                for prop in cat.Properties:
                    if prop.DisplayName == "Length":
                        val = prop.Value
                        if val.IsDoubleLength:
                            return val.ToDoubleLength()
                        elif val.IsDouble:
                            return val.ToDouble()
        return None


class ExportManager:
    """
    Exports wall data to an Excel file on the user's Desktop.
    """

    @staticmethod
    def ToExcel(data):
        df = pd.DataFrame(data)
        desktop = Path(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory))
        filepath = desktop / "Muros_MetrosLineales.xlsx"
        df.to_excel(str(filepath), index=False, sheet_name="Muros")
        print(f"Excel saved to: {filepath}")


# Entry point
data = WallAnalyzer.Run(doc)
ExportManager.ToExcel(data)

for w in data:
    print(f"  {w['Tipo de Muro']}: {w['Cantidad']} uds, {w['Metros Lineales (m)']} m")

print("Done!")
