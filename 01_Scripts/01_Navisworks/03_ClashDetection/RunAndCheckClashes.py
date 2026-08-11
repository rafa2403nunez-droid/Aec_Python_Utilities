# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr
import sys
from pathlib import Path

clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import Application

clr.AddReference("Autodesk.Navisworks.Clash")
from Autodesk.Navisworks.Api.Clash import DocumentClash, ClashResultStatus
bundlePath = (Path.home() / "AppData" / "Roaming" / "Autodesk" / "ApplicationPlugins" / "RAEN.Navisworks.PyNET.bundle" / "Contents" / "2024")
sys.path.append(str(bundlePath))
clr.AddReference("Raen.Core.Pynet.Resources")
from Raen.Core.Pynet.Resources import CastUtils  # type: ignore

from Autodesk.Navisworks.Api import Application


sys.path.append(str(Path.home() / "AppData" / "Roaming" / "Pynet" / "Library" / "01_Scripts" / "00_utils"))
from pynet_clash import get_clash_tests


class ClashManager:
    """
    Executes all clash tests in the active document and collects new results.
    """

    @staticmethod
    def RunAllTests(document):
        clashDocument = CastUtils.CastTo[DocumentClash](document.Clash)
        testsData = clashDocument.TestsData

        count = len(get_clash_tests(clashDocument))
        print(f"Running {count} clash test(s)...")
        testsData.TestsRunAllTests()
        print("All tests run. Reading results...")

        return clashDocument

    @staticmethod
    def CollectNewResults(clash_document):
        total_new = 0
        results = []

        for test in get_clash_tests(clash_document):
            new_count = sum(1 for c in test.Children if str(c.Status).upper() == str(ClashResultStatus.New).upper())
            total_new += new_count
            if new_count > 0:
                results.append({
                    "test": test.DisplayName,
                    "new": new_count,
                    "last_run": str(test.LastRun)
                })

        return total_new, results


class FeatureManager:
    """
    Entry point for running all clash tests and reporting new interferences.
    """

    @staticmethod
    def Run(document):
        clashDocument = ClashManager.RunAllTests(document)
        total_new, results = ClashManager.CollectNewResults(clashDocument)

        print(f"Total new clashes: {total_new}")
        for r in results:
            print(f"  {r['test']}: {r['new']} new")

        return {
            "total_new": total_new,
            "tests_with_new": results
        }


# Entry point
doc = Application.ActiveDocument
ia_Result = FeatureManager.Run(doc)
