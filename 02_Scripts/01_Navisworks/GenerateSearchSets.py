#region references

import clr
import sys
import os

sys.path.append("C:\\Program Files (x86)\\IronPython 2.7\\Lib")

clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import *

from System.Collections.Generic import List

clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")
from System.Windows.Forms import *
from System.Drawing import *

doc = __navisworks__  # type: ignore

#endregion

class SearchSetsManager():
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
    def CreateSet(value, selectionSets):
        """
        Creates a new Search Set in Navisworks based on a specific property value.

        The function searches elements that contain the property "Clash Test Code"
        either under the "Revit Type" or "Element" categories. The resulting set is
        added to the active document.

        Args:
            value (str): The property value used to filter and create the Search Set.
        """
        searchSet = Search()  # type: ignore
        searchSet.Locations = SearchLocations.DescendantsAndSelf # type: ignore
        searchSet.Selection.SelectAll()

        condition = SearchCondition.HasPropertyByDisplayName("Revit Type", "Clash Test Code")  # type: ignore
        conditionValue = condition.EqualValue(VariantData.FromDisplayString(value))  # type: ignore
        conditionList = List[SearchCondition]([conditionValue])  # type: ignore
        searchSet.SearchConditions.AddGroup(conditionList)

        conditionOr = SearchCondition.HasPropertyByDisplayName("Element", "Clash Test Code")  # type: ignore
        conditionValueOr = conditionOr.EqualValue(VariantData.FromDisplayString(value))  # type: ignore
        conditionListOr = List[SearchCondition]([conditionValueOr])  # type: ignore
        searchSet.SearchConditions.AddGroup(conditionListOr) 

        instance = SelectionSet(searchSet)  # type: ignore
        instance.DisplayName = value
        selectionSets.AddCopy(instance)



sets = SearchSetsManager.GetSets(doc)
setValues, filePath = None, None

with OpenFileDialog() as openDialog:
    openDialog.InitialDirectory = os.path.join(os.path.expanduser('~'), 'Desktop')
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
