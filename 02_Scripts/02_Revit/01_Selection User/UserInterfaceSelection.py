#region References

# Load the Python Standard and DesignScript Libraries
import clr
import Autodesk
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Structure import *
from Autodesk.Revit.Exceptions import OperationCanceledException

clr.AddReference('RevitAPIUI')
from Autodesk.Revit.UI import *
from Autodesk.Revit.UI.Selection import *

uidoc = __revit__.ActiveUIDocument #type:ignore
doc = uidoc.Document

#endregion

#region Pick Objects In User Interface

# Create ISelectionFilter Class. Select Elements that are Walls
class WallSelectionFilter(ISelectionFilter):
    def __init__(self, categoryName):
        self.categoryName = categoryName
    def AllowElement(self, element):
        if element.Category.Name == self.categoryName:
            return True
        else:
            return False
    def AllowReference(self, reference, position):
        return True

# Get Reference in the Revit Interface
references = None
try:
    references = uidoc.Selection.PickObjects(ObjectType.Element, WallSelectionFilter("Walls"), "Select a Walls and Select Finish: ")
except OperationCanceledException as ex:	
	TaskDialog.Show("Revit API", ex.Message)

# Get Element
if references != None:
    elements = [doc.GetElement(reference) for reference in references]
    print(elements)
else:
    print(ex.Message)

#endregion