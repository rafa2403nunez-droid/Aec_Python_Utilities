#region References

# Load the Python Standard and DesignScript Libraries
import string
import sys
import clr

clr.AddReference("ProtoGeometry")
from Autodesk.DesignScript.Geometry import *

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Structure import *

clr.AddReference("RevitAPIUI")
from Autodesk.Revit.UI import *
from Autodesk.Revit.UI.Selection import *

clr.AddReference("RevitNodes")
import Revit
clr.ImportExtensions(Revit.GeometryConversion)
clr.ImportExtensions(Revit.Elements)

clr.AddReference("RevitServices")
import RevitServices
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager
from System.Collections.Generic import List

doc = DocumentManager.Instance.CurrentDBDocument
uiapp = DocumentManager.Instance.CurrentUIApplication
app = uiapp.Application
uidoc = DocumentManager.Instance.CurrentUIApplication.ActiveUIDocument

# Import Windows form
clr.AddReference("System.Windows.Forms")
# Import System Drawing
clr.AddReference("System.Drawing")

import System
from System.Windows.Forms import*
from System.Drawing import*

clr.AddReference("System")
from System.Collections.Generic import List

# endregion

# region Get Doors of a Room

# Input Phase, necessary to obtain Rooms From Family Instance
phase = UnwrapElement(IN[0]) #type: ignore
category = UnwrapElement(IN[1]) #type: ignore

# Determinate if the Family Instance Category is Door or Window
if category.Id.ToString() != str(int(BuiltInCategory.OST_Doors)) or category.Id.ToString() != str(int(BuiltInCategory.OST_Windows)):
	OUT = "It is necessary to Select Doors or Windows Category"
if category.Id.ToString() == str(int(BuiltInCategory.OST_Doors)) or category.Id.ToString() == str(int(BuiltInCategory.OST_Windows)):
	categoryFilter = ElementCategoryFilter(category.Id)
	
# Collect Rooms
	rooms = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToElements()
	
# Collect Doors
	familyInstances = FilteredElementCollector(doc).WherePasses(categoryFilter).WhereElementIsNotElementType().ToElements()
	
# Definition Get Room from Doors
	def GetRoomDoors(familyInstances, rooms, phase):
		result = []
		for room in rooms:
			listInstance = []
			listRoom = []
			listInstance.append(room)
			for instance in familyInstances:
				if instance.__class__ == FamilyInstance and hasattr(instance, "ToRoom") and hasattr(instance, "FromRoom"):
					fromRoom = instance.FromRoom[phase]
					if instance.ToRoom[phase] != None and room.Id == instance.ToRoom[phase].Id:
						listRoom.append(instance)
					if instance.FromRoom[phase] != None and room.Id == instance.FromRoom[phase].Id:
						listRoom.append(instance)
			listInstance.append(listRoom)		
			result.append(listInstance)
		return result
	
OUT = GetRoomDoors(familyInstances, rooms, phase)

#endregion