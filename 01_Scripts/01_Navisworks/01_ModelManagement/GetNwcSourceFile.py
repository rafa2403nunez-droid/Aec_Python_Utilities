# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr
import sys
from pathlib import Path

clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import Application

bundle_base = Path.home() / "AppData" / "Roaming" / "Autodesk" / "ApplicationPlugins" / "Raen.Navisworks.Pynet.bundle" / "Contents"
bundlePath = next((d for d in bundle_base.iterdir() if d.is_dir() and (d / "Raen.Core.Pynet.Resources.dll").exists()), None)
sys.path.append(str(bundlePath))

doc = Application.ActiveDocument


class NwcSourceInspector:
    @staticmethod
    def Run(document):
        results = []
        for model in document.Models:
            source = NwcSourceInspector.GetSourceFile(model.RootItem)
            nwc_name = Path(model.FileName).name if model.FileName else "(unknown)"
            results.append({"nwc": nwc_name, "source_rvt": source})
            print(f"{nwc_name}  →  {source or '(not found)'}")
        return results

    @staticmethod
    def GetSourceFile(root_item):
        # Sample the first descendant that has the "Elemento" category with "Archivo de origen"
        for item in root_item.Descendants:
            for cat in item.PropertyCategories:
                if cat.DisplayName == "Elemento":
                    for prop in cat.Properties:
                        if prop.DisplayName == "Archivo de origen":
                            try:
                                val = prop.Value.ToDisplayString()
                                if val:
                                    return val
                            except:
                                pass
        return None


ia_Result = NwcSourceInspector.Run(doc)
