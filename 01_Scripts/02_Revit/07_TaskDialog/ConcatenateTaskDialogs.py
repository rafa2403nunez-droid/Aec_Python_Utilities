# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr
import webbrowser

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import (TaskDialog, TaskDialogCommonButtons,
                                TaskDialogIcon, TaskDialogCommandLinkId,
                                TaskDialogResult)

app = __revit__.Application  #type:ignore
doc = __revit__.ActiveUIDocument.Document  #type:ignore


class TaskDialogDemo:
    @staticmethod
    def ShowAppInfo(application):
        dlg = TaskDialog("Revit API")
        dlg.TitleAutoPrefix = False
        dlg.MainInstruction = "Revit Version"
        dlg.MainContent = application.VersionName
        dlg.CommonButtons = TaskDialogCommonButtons.Ok
        dlg.Show()

    @staticmethod
    def ShowDocInfo(document):
        dlg = TaskDialog("Revit API")
        dlg.TitleAutoPrefix = False
        dlg.MainInstruction = "Document Info"
        dlg.MainContent = f"Title: {document.Title}"
        dlg.CommonButtons = TaskDialogCommonButtons.Ok
        dlg.Show()

    @staticmethod
    def Run(app, doc):
        main = TaskDialog("Revit API")
        main.TitleAutoPrefix = False
        main.MainInstruction = "Information to Show"
        main.MainContent = "Example of TaskDialog with Command Links"
        main.AddCommandLink(TaskDialogCommandLinkId.CommandLink1,
                            "Show Revit version info", "Application information")
        main.AddCommandLink(TaskDialogCommandLinkId.CommandLink2,
                            "Show document info", "Current document information")
        main.ExpandedContent = "This demonstrates chained TaskDialogs using command links."
        main.MainIcon = TaskDialogIcon.TaskDialogIconInformation
        main.CommonButtons = TaskDialogCommonButtons.Cancel
        main.FooterText = '<a href="https://github.com/rafa2403nunez-droid/PyNet">PyNET on GitHub</a>'

        result = main.Show()

        if result == TaskDialogResult.CommandLink1:
            TaskDialogDemo.ShowAppInfo(app)
        elif result == TaskDialogResult.CommandLink2:
            TaskDialogDemo.ShowDocInfo(doc)
        else:
            dlg = TaskDialog("Revit API")
            dlg.TitleAutoPrefix = False
            dlg.MainInstruction = "Cancelled"
            dlg.CommonButtons = TaskDialogCommonButtons.Ok
            dlg.Show()


TaskDialogDemo.Run(app, doc)
