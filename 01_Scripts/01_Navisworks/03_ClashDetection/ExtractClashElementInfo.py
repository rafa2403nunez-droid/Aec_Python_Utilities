# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

#region references
import clr
import sys
from pathlib import Path

clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import Application

clr.AddReference("Autodesk.Navisworks.Clash")
from Autodesk.Navisworks.Api.Clash import DocumentClash
clr.AddReference("System.Windows.Forms")
from System.Windows.Forms import MessageBox, MessageBoxButtons, MessageBoxIcon

bundlePath = (Path.home() / "AppData" / "Roaming" / "Autodesk" / "ApplicationPlugins" / "RAEN.Navisworks.PyNET.bundle" / "Contents" / "2024")
sys.path.append(str(bundlePath))

clr.AddReference("Raen.Core.Pynet.Resources")
from Raen.Core.Pynet.Resources import CastUtils  # type: ignore

from Autodesk.Navisworks.Api import Application
doc = Application.ActiveDocument

#endregion


sys.path.append(str(Path.home() / "AppData" / "Roaming" / "Pynet" / "Library" / "01_Scripts" / "00_utils"))
from pynet_clash import get_clash_tests


class ElementInfoExtractor:
    DIAM_PROPS = ("Diámetro", "Diametro", "Diameter", "Tamaño")

    @staticmethod
    def GetInfo(model_item):
        info = {"name": "", "category": "", "pynet": "", "diameter": ""}
        nodes = [model_item] + list(model_item.Ancestors)
        for node in nodes:
            for cat in node.PropertyCategories:
                if cat.Name == "LcRevitData_Element":
                    for prop in cat.Properties:
                        dn = prop.DisplayName
                        try:
                            v = prop.Value.ToDisplayString()
                        except:
                            v = ""
                        if dn in ("Nombre", "Name") and not info["name"]:
                            info["name"] = v
                        if dn in ("Categoría", "Category") and not info["category"]:
                            info["category"] = v
                        if not info["diameter"] and dn in ElementInfoExtractor.DIAM_PROPS and v and v != "0":
                            info["diameter"] = v
                if cat.Name in ("LcRevitData_TypeCustom", "LcRevitData_Type", "lcldrevit_tab_type"):
                    for prop in cat.Properties:
                        if prop.DisplayName == "PYNET_Classification" and not info["pynet"]:
                            try:
                                info["pynet"] = prop.Value.ToDisplayString()
                            except:
                                pass
        return info


class ClashInfoManager:

    @staticmethod
    def Extract(document):
        clashDoc = CastUtils.CastTo[DocumentClash](document.Clash)

        results = []
        clash_index = 1
        for test in get_clash_tests(clashDoc):
            for r in test.Children:
                try:
                    depth = round(r.Distance * 304.8, 1)
                except:
                    depth = None
                a = ElementInfoExtractor.GetInfo(r.Item1)
                b = ElementInfoExtractor.GetInfo(r.Item2)
                results.append({
                    "idx": clash_index,
                    "test": test.DisplayName,
                    "status": str(r.Status),
                    "depth_mm": depth,
                    "a_name": a["name"], "a_category": a["category"],
                    "a_pynet": a["pynet"], "a_diameter": a["diameter"],
                    "b_name": b["name"], "b_category": b["category"],
                    "b_pynet": b["pynet"], "b_diameter": b["diameter"],
                })
                clash_index += 1

        return results

    @staticmethod
    def PrintResults(results):
        status_counts = {}
        for r in results:
            s = r["status"]
            status_counts[s] = status_counts.get(s, 0) + 1

        print(f"Total clash results: {len(results)}")
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count}")
        print("")

        for r in results:
            diam_a = f" ({r['a_diameter']})" if r["a_diameter"] else ""
            diam_b = f" ({r['b_diameter']})" if r["b_diameter"] else ""
            print(
                f"[{r['idx']:02d}] {r['test']} | {r['status']} | {r['depth_mm']} mm | "
                f"{r['a_pynet']}{diam_a} vs {r['b_pynet']}{diam_b} | "
                f"{r['a_name']} / {r['b_name']}"
            )

    @staticmethod
    def ShowSummaryDialog(results):
        status_counts = {}
        for r in results:
            s = r["status"]
            status_counts[s] = status_counts.get(s, 0) + 1

        lines = [f"Total: {len(results)} clash results", ""]
        for status, count in sorted(status_counts.items()):
            lines.append(f"  {status}: {count}")

        MessageBox.Show(
            "\n".join(lines),
            "Clash Element Info",
            MessageBoxButtons.OK,
            MessageBoxIcon.Information
        )


# Entry point
results = ClashInfoManager.Extract(doc)
ClashInfoManager.PrintResults(results)
ClashInfoManager.ShowSummaryDialog(results)

#endregion
