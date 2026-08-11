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
bundlePath = (
    Path.home()
    / "AppData" / "Roaming" / "Autodesk" / "ApplicationPlugins"
    / "RAEN.Navisworks.PyNET.bundle" / "Contents" / "2027"
)
sys.path.append(str(bundlePath))
clr.AddReference("Raen.Core.Pynet.Resources")
from Raen.Core.Pynet.Resources import CastUtils  # type: ignore

doc = Application.ActiveDocument

#endregion


# ─── Configuration ────────────────────────────────────────────────────────────

TOLERANCE_MM = 15.0  # target tolerance in millimetres

# Optional: target only specific tests by display name.
# Leave empty to apply to ALL tests.
TARGET_TESTS: list[str] = []

# ─── Helpers ──────────────────────────────────────────────────────────────────

MM_TO_FEET = 1 / (0.3048 * 1000)


def get_clash_doc():
    return CastUtils.CastTo[DocumentClash](doc.Clash)


sys.path.append(str(Path.home() / "AppData" / "Roaming" / "Pynet" / "Library" / "01_Scripts" / "00_utils"))
from pynet_clash import get_clash_tests


# ─── Approach A: edit via copy (official API pattern) ─────────────────────────
#
# ClashTest objects are read-only by ownership — you cannot assign .Tolerance
# directly. The supported way is to create a detached copy, mutate it, then
# apply the copy back with TestsEditTestFromCopy.

def set_tolerance_via_copy(tolerance_mm: float, target_tests: list[str] = None):
    clash_doc = get_clash_doc()
    tests_data = clash_doc.TestsData
    tolerance_ft = tolerance_mm * MM_TO_FEET
    updated = []

    for test in get_clash_tests(clash_doc):
        if target_tests and test.DisplayName not in target_tests:
            continue

        old_mm = round(test.Tolerance / MM_TO_FEET, 2)
        copy = test.CreateCopy()
        copy.set_Tolerance(tolerance_ft)
        tests_data.TestsEditTestFromCopy(test, copy)
        updated.append({"test": test.DisplayName, "from_mm": old_mm, "to_mm": tolerance_mm})
        print(f"  {test.DisplayName}: {old_mm} mm → {tolerance_mm} mm")

    return updated


# ─── Approach B: duplicate test, set tolerance on the new copy ─────────────────
#
# An alternative when you want to keep the original test intact alongside a
# new variant. DuplicateTest creates an independent copy in the document;
# you then rename it and set its tolerance via the same copy mechanism.
# Useful for side-by-side comparisons without overwriting the source test.

def duplicate_test_with_tolerance(test_name: str, new_name: str, tolerance_mm: float):
    clash_doc = get_clash_doc()
    tests_data = clash_doc.TestsData
    tolerance_ft = tolerance_mm * MM_TO_FEET

    source = next(
        (t for t in get_clash_tests(clash_doc) if t.DisplayName == test_name),
        None,
    )
    if source is None:
        print(f"Test not found: {test_name}")
        return None

    duplicate = source.DuplicateTest()

    # Set name on the duplicate
    tests_data.TestsEditDisplayName(duplicate, new_name)

    # Set tolerance on the duplicate via copy pattern
    copy = duplicate.CreateCopy()
    copy.set_Tolerance(tolerance_ft)
    tests_data.TestsEditTestFromCopy(duplicate, copy)

    print(f"  Duplicated '{test_name}' → '{new_name}' @ {tolerance_mm} mm")
    return {"source": test_name, "duplicate": new_name, "tolerance_mm": tolerance_mm}


# ─── Entry point ──────────────────────────────────────────────────────────────

class FeatureManager:

    @staticmethod
    def Run():
        # ── Option 1: update all tests in place ──
        print("Setting tolerance via copy (Approach A)...")
        results_a = set_tolerance_via_copy(TOLERANCE_MM, TARGET_TESTS or None)

        # ── Option 2: duplicate each test and set a different tolerance ──
        # Uncomment and adapt to use side-by-side comparison approach:
        #
        # print("Duplicating tests with new tolerance (Approach B)...")
        # results_b = []
        # for test in get_clash_tests(get_clash_doc()):
        #     dup_name = f"{test.DisplayName}_15mm"
        #     result = duplicate_test_with_tolerance(test.DisplayName, dup_name, TOLERANCE_MM)
        #     if result:
        #         results_b.append(result)

        return {
            "approach": "A - edit via copy",
            "tolerance_mm": TOLERANCE_MM,
            "updated": results_a,
        }


ia_Result = FeatureManager.Run()
