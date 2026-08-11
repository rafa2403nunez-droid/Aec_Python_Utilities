# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

#region references

import clr
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import Application, Comment, CommentCollection, CommentStatus

clr.AddReference("Autodesk.Navisworks.Clash")
from Autodesk.Navisworks.Api.Clash import DocumentClash, ClashResultStatus
clr.AddReference("System.Windows.Forms")
from System.Windows.Forms import OpenFileDialog, DialogResult, MessageBox, MessageBoxButtons, MessageBoxIcon

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


class ClashResultData:
    """
    Data container for a single clash result entry parsed from an XML export.
    Stores the test name, result GUID, status and optional comments.
    """

    def __init__(self, testName, guid, status, comment):
        self.testName = testName
        self.guid = guid
        self.status = status
        self.comment = comment

    @property
    def TestName(self):
        return self.testName

    @property
    def Guid(self):
        return self.guid

    @property
    def Status(self):
        return self.status

    @property
    def Comment(self):
        return self.comment


class DialogManager:
    """
    Handles user-facing dialogs for clash result import operations.
    Provides file browser and confirmation message boxes.
    """

    @staticmethod
    def ShowOpenFileDialog():
        openDialog = OpenFileDialog()
        openDialog.InitialDirectory = str(Path.home() / "Desktop")
        openDialog.Filter = "xml files (*.xml)|*.xml|All files (*.*)|*.*"

        if openDialog.ShowDialog() == DialogResult.OK:
            return openDialog.FileName
        return None

    @staticmethod
    def DataImportedDialog():
        MessageBox.Show(
            "Clash results updated, status changed to approved or reviewed",
            "Update Clash Results",
            MessageBoxButtons.OK,
            MessageBoxIcon.Information
        )


class DataManager:
    """
    Parses clash result data from Navisworks XML export files.
    Extracts approved and reviewed results with their comments for re-import.
    """

    @staticmethod
    def GetClashesData():
        xmlPath = DialogManager.ShowOpenFileDialog()
        if not xmlPath:
            raise Exception("No XML file selected")

        tree = ET.parse(xmlPath)
        root = tree.getroot()

        dataResults = []

        for clashTest in root.iter("clashtest"):
            clashTestName = clashTest.get("name")
            for clashResult in clashTest.iter("clashresult"):
                status = (clashResult.get("status") or "").lower()
                if status not in ("approved", "reviewed"):
                    continue
                guid = clashResult.get("guid")
                comment_nodes = clashResult.findall("./comments/comment/body")
                comments = None
                if comment_nodes:
                    comments = CommentCollection()

                    for node in comment_nodes:
                        comments.Add(Comment(node.text, CommentStatus.New))
                dataResults.append(
                    ClashResultData(
                        clashTestName,
                        guid,
                        status,
                        comments
                    )
                )

        return dataResults

class ClashManager:
    """
    Handles re-importing clash result statuses and comments into the active document.
    Matches results by GUID and updates their status to approved or reviewed.
    """

    @staticmethod
    def ImportClashResults(dataResults):

        clashDoc = CastUtils.CastTo[DocumentClash](doc.Clash)
        documentClashTests = clashDoc.TestsData
        tests = get_clash_tests(clashDoc)

        for test in tests:
            for data in dataResults:
                if data.TestName == test.DisplayName:
                    for children in test.Children:

                        if str(children.Guid) == data.Guid and str(children.Status).upper() != data.Status.upper():

                            # Add comments if present
                            if data.Comment != None:
                                documentClashTests.TestsEditResultComments(children, data.Comment)

                            # Apply new status
                            if data.Status.upper() == str(ClashResultStatus.Approved).upper():
                                documentClashTests.TestsEditResultStatus(children, ClashResultStatus.Approved)

                            elif data.Status.upper() == str(ClashResultStatus.Reviewed).upper():
                                documentClashTests.TestsEditResultStatus(children, ClashResultStatus.Reviewed)


        DialogManager.DataImportedDialog()



ClashManager.ImportClashResults(DataManager.GetClashesData())