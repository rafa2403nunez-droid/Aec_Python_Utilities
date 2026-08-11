# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

#region references

import clr
import sys
from pathlib import Path

clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import Application, PublishProperties

clr.AddReference("System.Windows.Forms")
from System.Windows.Forms import MessageBox, MessageBoxButtons, MessageBoxIcon

from System.Collections.Generic import List
from datetime import datetime

bundlePath = (Path.home()/ "AppData"/ "Roaming"/ "Autodesk"/ "ApplicationPlugins"/ "RAEN.Navisworks.PyNET.bundle"/ "Contents"/ "2024")
NavisworksinconPath = (Path.home() / "AppData" / "Roaming" / "Autodesk" / "ApplicationPlugins" / "Raen.Navisworks.Pynet.bundle" / "manage.ico")

sys.path.append(str(bundlePath))

clr.AddReference("Raen.Core.Pynet.Resources")

from Raen.Core.Pynet.Resources import CastUtils  # type: ignore

from Autodesk.Navisworks.Api import Application 
doc = Application.ActiveDocument

#endregion


class ModelManagement:
    """
    Utility class for managing Navisworks models using PythonNET.
    Provides methods for opening, appending, listing, and publishing NWD files.
    """

    @staticmethod
    def GetModelsList(document):
        """
        Lists all model files currently loaded in the active document.

        Args:
            document (Autodesk.Navisworks.Api.Document): The active Navisworks document.
        """
        models = document.Models.GetEnumerator()
        names = [model.FileName for model in models]
        MessageBox.Show(
            "\n".join(names),
            "Loaded Models",
            MessageBoxButtons.OK,
            MessageBoxIcon.Information
        )

    @staticmethod
    def OpenFile(path, document, useTry):
        """
        Opens a Navisworks file (.NWF, .NWD, .NWC).

        Args:
            path (str): The file path to open.
            document (Autodesk.Navisworks.Api.Document): The current document.
            useTry (bool): If True, uses TryOpenFile() to handle errors gracefully.
        """
        if useTry:
            document.TryOpenFile(path)
        else:
            document.OpenFile(path)

    @staticmethod
    def AppendFiles(document, filePaths, useTry):
        """
        Appends one or more model files to the current Navisworks document.

        Args:
            document (Autodesk.Navisworks.Api.Document): The current document.
            filePaths (list[str]): List of file paths to append.
            useTry (bool): If True, uses TryAppendFiles() for safe execution.
        """
        if useTry:
            document.TryAppendFiles(List[str](filePaths))
        else:
            document.AppendFiles(List[str](filePaths))

    @staticmethod
    def PublishModel(document, path):
        """
        Publishes the current Navisworks document as an NWD file.

        Args:
            document (Autodesk.Navisworks.Api.Document): The active Navisworks document.
            path (str): The output path for the published NWD file.
        """
        properties = PublishProperties()

        properties.AllowResave = True
        properties.Author = ""
        properties.Comments = ""
        properties.Copyright = ""
        properties.DisplayAtPassword = True
        properties.DisplayOnOpen = True
        properties.EmbedDatabaseProperties = True
        properties.EmbedTextures = True
        properties.ExpiryDate = ""
        properties.Keywords = ""
        properties.PreventObjectPropertyExport = False
        properties.PublishDate = datetime.now()
        properties.PublishedFor = ""
        properties.Publisher = ""
        properties.Subject = ""
        properties.Title = ""

        properties.SetPassword("Password")

        document.PublishFile(path, properties)

#endregion
