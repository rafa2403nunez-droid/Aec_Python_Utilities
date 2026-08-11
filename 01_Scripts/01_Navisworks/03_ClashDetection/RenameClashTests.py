# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

#region references

import clr
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import Application

clr.AddReference("Autodesk.Navisworks.Clash")
from Autodesk.Navisworks.Api.Clash import DocumentClash
clr.AddReference("System.Windows.Forms")
from System.Windows.Forms import MessageBox, MessageBoxButtons, MessageBoxIcon

bundlePath = (Path.home()/ "AppData"/ "Roaming"/ "Autodesk"/ "ApplicationPlugins"/ "RAEN.Navisworks.PyNET.bundle"/ "Contents"/ "2024")
NavisworksinconPath = (Path.home() / "AppData" / "Roaming" / "Autodesk" / "ApplicationPlugins" / "Raen.Navisworks.Pynet.bundle" / "manage.ico")

sys.path.append(str(bundlePath))

clr.AddReference("Raen.Core.Pynet.Resources")

from Raen.Core.Pynet.Resources import CastUtils  # type: ignore

from Autodesk.Navisworks.Api import Application 
doc = Application.ActiveDocument

#endregion

sys.path.append(str(Path.home() / "AppData" / "Roaming" / "Pynet" / "Library" / "01_Scripts" / "00_utils"))
from pynet_clash import get_clash_tests


class DialogManager:
    """
    Handles user-facing dialogs for clash test rename operations.
    """

    @staticmethod
    def NameUpdateDialog():
        MessageBox.Show(
            "Clash names updated with the especified prefix",
            "Update Clash names",
            MessageBoxButtons.OK,
            MessageBoxIcon.Information
        )

class ClashManager:
    """
    Renames all clash tests in the active document by adding a prefix to their display names.
    """

    @staticmethod
    def RenameTests():
        clashDoc = CastUtils.CastTo[DocumentClash](doc.Clash)
        documentClashTests = clashDoc.TestsData
        tests = get_clash_tests(clashDoc)

        for test in tests:
            documentClashTests.TestsEditDisplayName(test, "PrefixTest_" + test.DisplayName)

        DialogManager.NameUpdateDialog()

ClashManager.RenameTests()