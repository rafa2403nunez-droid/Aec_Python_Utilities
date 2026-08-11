# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

#region references

import clr
import sys
from pathlib import Path

clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import (
    Application, Search, SearchLocations, SearchCondition, VariantData, SelectionSet
)

clr.AddReference("System.Windows.Forms")
from System.Windows.Forms import OpenFileDialog, DialogResult, MessageBox, MessageBoxButtons, MessageBoxIcon

from System.Collections.Generic import List

bundlePath = (Path.home()/ "AppData"/ "Roaming"/ "Autodesk"/ "ApplicationPlugins"/ "RAEN.Navisworks.PyNET.bundle"/ "Contents"/ "2024")
NavisworksinconPath = (Path.home() / "AppData" / "Roaming" / "Autodesk" / "ApplicationPlugins" / "Raen.Navisworks.Pynet.bundle" / "manage.ico")

sys.path.append(str(bundlePath))

clr.AddReference("Raen.Core.Pynet.Resources")

from Raen.Core.Pynet.Resources import CastUtils  # type: ignore

from Autodesk.Navisworks.Api import Application 
doc = Application.ActiveDocument

#endregion

class SearchSetsManager():
    """
    Manages Navisworks Selection Sets creation and retrieval.
    Provides methods for reading existing sets and generating new ones from property conditions.
    """

    @staticmethod
    def GetSets(document):
        """
        Retrieves all Selection Sets from the active Navisworks document.

        Args:
            document (Autodesk.Navisworks.Api.Document):
                The currently active Navisworks document.

        Returns:
            Autodesk.Navisworks.Api.DocumentSelectionSets:
                A collection object containing all the Selection Sets
                currently defined in the document.
        """
        return document.SelectionSets

    @staticmethod
    def ClearSets(document):
        """
        Removes all Selection Sets from the active Navisworks document.
        No transaction needed — write operations on DocumentSelectionSets are direct.

        Args:
            document (Autodesk.Navisworks.Api.Document):
                The currently active Navisworks document.
        """
        document.SelectionSets.Clear()
    @staticmethod
    def CreateSet(value, selectionSets):
        """
        Creates a new Search Set in Navisworks based on a specific property value.

        The function searches elements that contain the property "Clash Test Code"
        either under the "Revit Type" or "Element" categories. The resulting set is
        added to the active document.

        Args:
            value (str): The property value used to filter and create the Search Set.
        """
        searchSet = Search()
        searchSet.Locations = SearchLocations.DescendantsAndSelf
        searchSet.Selection.SelectAll()

        condition = SearchCondition.HasPropertyByDisplayName("Revit Type", "Clash Test Code")
        conditionValue = condition.EqualValue(VariantData.FromDisplayString(value))
        conditionList = List[SearchCondition]([conditionValue])
        searchSet.SearchConditions.AddGroup(conditionList)

        conditionOr = SearchCondition.HasPropertyByDisplayName("Element", "Clash Test Code")
        conditionValueOr = conditionOr.EqualValue(VariantData.FromDisplayString(value))
        conditionListOr = List[SearchCondition]([conditionValueOr])
        searchSet.SearchConditions.AddGroup(conditionListOr) 

        instance = SelectionSet(searchSet)
        instance.DisplayName = value
        selectionSets.AddCopy(instance)

sets = SearchSetsManager.GetSets(doc)
setValues, filePath = None, None

with OpenFileDialog() as openDialog:
    openDialog.InitialDirectory = str(Path.home() / "Desktop")
    openDialog.Filter = "txt files (*.txt)|*.txt|All files (*.*)|*.*"

    if openDialog.ShowDialog() == DialogResult.OK:
        filePath = openDialog.FileName
        if filePath is not None:
            with open(filePath, "r") as file:
                setsValues = file.readlines()
                file.close()

for value in setsValues:
    name = value.replace("\n", "")
    if name != "":
        SearchSetsManager.CreateSet(name, sets)

MessageBox.Show(
    "Search Sets created successfully.",
    "Navisworks API",
    MessageBoxButtons.OK,
    MessageBoxIcon.Information
)
