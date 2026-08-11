# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr
from pathlib import Path
import pandas as pd

clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import Application

from System import Environment

doc = Application.ActiveDocument


class QueryCategory:
    """
    Iterates all model items recursively and collects unique values
    for the Custom category parameter, counting occurrences of each.
    Results are printed as a formatted table and exported to Excel.
    """

    @staticmethod
    def Run(document):
        print("Searching for MDE_Categoria values across the model...")
        values = {}
        total = [0]

        def search_items(items):
            """Recursively traverses the model tree collecting MDE_Categoria values."""
            for item in items:
                for cat in item.PropertyCategories:
                    for prop in cat.Properties:
                        if prop.DisplayName == "MDE_Categoria" or prop.Name == "MDE_Categoria":
                            total[0] += 1
                            val = prop.Value
                            display_val = str(val.ToDisplayString()) if val is not None else ""
                            if display_val not in values:
                                values[display_val] = 0
                            values[display_val] += 1
                if item.Children is not None:
                    search_items(item.Children)

        search_items(document.Models.RootItems)

        # Sort by count descending
        sorted_values = sorted(values.items(), key=lambda x: -x[1])

        # Print summary and formatted table
        print(f"\nTotal elements with MDE_Categoria: {total[0]}")
        print(f"Unique values: {len(values)}\n")
        print(f"{'Value':<40} {'Count':>8}")
        print("-" * 50)
        for v, c in sorted_values:
            label = v if v.strip() != "" else "(empty)"
            print(f"{label:<40} {c:>8}")

        # Export results to Excel on Desktop
        ExportManager.ToExcel(sorted_values)


class ExportManager:
    """
    Exports the unique MDE_Categoria values and counts to an Excel file
    on the user's Desktop.
    """

    @staticmethod
    def ToExcel(sorted_values):
        desktop = Path(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory))
        excel_path = desktop / "MDE_Categoria_UniqueValues.xlsx"
        df = pd.DataFrame(sorted_values, columns=["MDE_Categoria", "Count"])
        df.to_excel(str(excel_path), index=False)
        print(f"\nExcel exported to: {excel_path}")


# Entry point
QueryCategory.Run(doc)
