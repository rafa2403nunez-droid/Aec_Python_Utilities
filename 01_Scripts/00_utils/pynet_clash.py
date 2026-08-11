# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

"""
PyNET shared clash helpers — version-tolerant access to Navisworks clash tests.

Why this module exists
----------------------
The Navisworks Clash API changed between **2025 and 2026/2027**:
  - Navisworks 2025 and earlier exposed `DocumentClashTests.Tests` (a flat collection).
  - 2026/2027 removed `.Tests`; tests live under `TestsData.Value.TestsRoot.Children`.
Since each user may run a different Navisworks version, scripts must never call `.Tests`
or `.TestsData.Value.TestsRoot.Children` directly. Use `get_clash_tests()` — it tries the old
API and falls back to the new one (EAFP), so the same script runs unchanged on any version.

Confirmed live on Navisworks 2027:
  DocumentClash.TestsData          -> DocumentClashTests
  DocumentClashTests.Value         -> ClashTestsData
  ClashTestsData.TestsRoot.Children -> the ClashTest items

Usage from a script
--------------------
    import sys
    from pathlib import Path
    sys.path.append(str(Path.home() / "AppData" / "Roaming" / "Pynet" / "Library"
                        / "01_Scripts" / "00_utils"))
    from pynet_clash import get_clash_tests, iter_results

    clashDoc = CastUtils.CastTo[DocumentClash](document.Clash)
    for test in get_clash_tests(clashDoc):
        for result in iter_results(test):
            ...

See docs/navisworks.md for the full explanation.
"""


def get_clash_tests(clash_document):
    """
    List of the ClashTest items in the document, regardless of Navisworks version.

    `clash_document` is `document.Clash` cast to `DocumentClash` (use CastUtils.CastTo).
    - Navisworks 2025 and earlier: returns `DocumentClashTests.Tests` (flat collection).
    - Navisworks 2026/2027: `.Tests` was removed -> returns `TestsData.Value.TestsRoot.Children`.

    Note: assumes tests live at the root (not nested in clash-test folders), which matches
    how this project organises them.
    """
    tests_data = clash_document.TestsData
    try:
        return list(tests_data.Tests)                       # Navisworks 2025 and earlier
    except AttributeError:
        return list(tests_data.Value.TestsRoot.Children)    # Navisworks 2026 / 2027


def iter_results(test):
    """
    Yields all clash results under a test, flattening `ClashResultGroup` items so a
    group's N results are all visited. Iterating `test.Children` directly would count
    a group as 1 (or skip it entirely on a `CastTo[ClashResult]`, which returns None).
    """
    for child in test.Children:
        if child.IsGroup:
            for r in child.Children:
                yield r
        else:
            yield child
