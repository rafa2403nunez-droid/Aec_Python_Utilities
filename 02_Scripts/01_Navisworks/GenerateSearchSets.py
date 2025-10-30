#region references

import clr
import sys

sys.path.append("C:\\Program Files (x86)\\IronPython 2.7\\Lib")
import os

clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import *

from System.Collections.Generic import List

#Import Windows form
clr.AddReference("System.Windows.Forms")
# Import System Drawing
clr.AddReference("System.Drawing")

from System.Windows.Forms import*
from System.Drawing import*

doc = __navisworks__ #type:ignore
selectionSets = doc.SelectionSets

#endregion

def CreateSet(value):
    searchSet = Search() #type:ignore
    searchSet.Locations = SearchLocations.DescendantsAndSelf #type:ignore
    searchSet.Selection.SelectAll()
    condition = SearchCondition.HasPropertyByDisplayName("Revit Type", "Clash Test Code") #type:ignore
    conditionValue = condition.EqualValue(VariantData.FromDisplayString(value)) #type:ignore
    conditionList = List[SearchCondition]([conditionValue]) #type:ignore
    searchSet.SearchConditions.AddGroup(conditionList) #type:ignore
    conditionOr = SearchCondition.HasPropertyByDisplayName("Element", "Clash Test Code") #type:ignore
    conditionValueOr = conditionOr.EqualValue(VariantData.FromDisplayString(value)) #type:ignore
    conditionListOr = List[SearchCondition]([conditionValueOr]) #type:ignore
    searchSet.SearchConditions.AddGroup(conditionListOr) #type:ignore
    instance = SelectionSet(searchSet) #type:ignore
    instance.DisplayName = value
    selectionSets.AddCopy(instance)

setValues, filePath = None, None

with OpenFileDialog() as openDialog:
	openDialog.InitialDirectory = os.path.join(os.path.expanduser('~'), 'Desktop')
	openDialog.Filter = "txt files (*.txt)|*.txt|All files (*.*)|*.*"
	if openDialog.ShowDialog() == DialogResult.OK:
		filePath = openDialog.FileName
		if filePath != None:
			with open(filePath, "r") as file:
				setsValues = file.readlines()
				file.close()

for value in setsValues:
	name = value.replace("\n", "")
	if name != "":
	    CreateSet(name)

MessageBox.Show("Search Sets created correctly", "Navisworks API", MessageBoxButtons.OK, MessageBoxIcon.Information)