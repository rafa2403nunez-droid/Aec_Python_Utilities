# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr
import sys
import json
from pathlib import Path
from datetime import datetime
from System import Environment

clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import Application

clr.AddReference("Autodesk.Navisworks.Clash")
from Autodesk.Navisworks.Api.Clash import DocumentClash
bundle_base = Path.home() / "AppData" / "Roaming" / "Autodesk" / "ApplicationPlugins" / "Raen.Navisworks.Pynet.bundle" / "Contents"
bundlePath = next((d for d in bundle_base.iterdir() if d.is_dir() and (d / "Raen.Core.Pynet.Resources.dll").exists()), None)
sys.path.append(str(bundlePath))
clr.AddReference("Raen.Core.Pynet.Resources")
from Raen.Core.Pynet.Resources import CastUtils

doc = Application.ActiveDocument


sys.path.append(str(Path.home() / "AppData" / "Roaming" / "Pynet" / "Library" / "01_Scripts" / "00_utils"))
from pynet_clash import get_clash_tests


class ElementExtractor:
    @staticmethod
    def get_cat_prop(node, cat_name, prop_name):
        for cat in node.PropertyCategories:
            if cat.Name == cat_name:
                for prop in cat.Properties:
                    if prop.DisplayName == prop_name:
                        try:
                            return prop.Value.ToDisplayString()
                        except:
                            pass
        return None

    @staticmethod
    def extract(item):
        revit_id = None
        pynet_code = None
        rvt_model = None
        name = item.DisplayName
        category = None
        nwc_file = None

        current = item
        for _ in range(10):
            if current is None:
                break

            if revit_id is None:
                val = ElementExtractor.get_cat_prop(current, "LcRevitId", "Valor")
                if val:
                    try:
                        revit_id = int(val)
                        name = current.DisplayName
                    except:
                        pass

            if pynet_code is None:
                pynet_code = (
                    ElementExtractor.get_cat_prop(current, "LcRevitData_Type", "PYNET_Classification") or
                    ElementExtractor.get_cat_prop(current, "lcldrevit_tab_type", "PYNET_Classification") or
                    ElementExtractor.get_cat_prop(current, "LcRevitData_TypeCustom", "PYNET_Classification")
                )

            if rvt_model is None:
                rvt_model = ElementExtractor.get_cat_prop(current, "Document", "Title")

            if category is None:
                category = ElementExtractor.get_cat_prop(current, "Category", "Name")

            if nwc_file is None and current.ClassDisplayName == "Archivo":
                nwc_file = current.DisplayName

            if revit_id and pynet_code and rvt_model and category and nwc_file:
                break

            try:
                current = current.Parent
            except:
                break

        return {
            "revit_id": revit_id,
            "name": name,
            "pynet_code": pynet_code,
            "category": category,
            "rvt_model": rvt_model,
            "nwc_file": nwc_file,
        }


class ClashExporter:
    @staticmethod
    def iter_results(test):
        for child in test.Children:
            if child.IsGroup:
                for r in child.Children:
                    yield r
            else:
                yield child

    @staticmethod
    def collect(clash_document):
        clashes = []
        idx = 1
        for test in get_clash_tests(clash_document):
            for r in ClashExporter.iter_results(test):
                c = r.Center
                clashes.append({
                    "id": idx,
                    "test": test.DisplayName,
                    "status": str(r.Status),
                    "center_ft": {"x": round(c.X, 6), "y": round(c.Y, 6), "z": round(c.Z, 6)},
                    "element_a": ElementExtractor.extract(r.Item1),
                    "element_b": ElementExtractor.extract(r.Item2),
                })
                idx += 1
        return clashes

    @staticmethod
    def run(document):
        clashDoc = CastUtils.CastTo[DocumentClash](document.Clash)

        print("Collecting clash results...")
        clashes = ClashExporter.collect(clashDoc)

        doc_name = Path(document.FileName).stem if document.FileName else "Unknown"
        payload = {
            "export_date": datetime.now().isoformat(),
            "source_model": doc_name,
            "total_clashes": len(clashes),
            "clashes": clashes,
        }

        desktop = Environment.GetFolderPath(Environment.SpecialFolder.Desktop)
        out_path = Path(desktop) / f"ClashExport_{doc_name}.json"

        with open(str(out_path), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        from collections import Counter
        counts = Counter(c["status"] for c in clashes)
        summary = ", ".join(f"{v} {k}" for k, v in sorted(counts.items()))
        print(f"Exported {len(clashes)} clashes ({summary})")
        print(f"Output: {out_path}")

        return payload


result = ClashExporter.run(doc)
