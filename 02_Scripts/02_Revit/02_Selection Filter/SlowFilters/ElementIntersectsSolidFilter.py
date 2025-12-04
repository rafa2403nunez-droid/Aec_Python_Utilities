#region References

# Load the Python Standard and DesignScript Libraries
import string
import sys
import clr

clr.AddReference('ProtoGeometry')
from Autodesk.DesignScript.Geometry import *

clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Structure import *

clr.AddReference('RevitAPIUI')
from Autodesk.Revit.UI import *

clr.AddReference('RevitNodes')
import Revit
clr.ImportExtensions(Revit.GeometryConversion)
clr.ImportExtensions(Revit.Elements)

clr.AddReference('RevitServices')
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

clr.AddReference('System')
from System.Collections.Generic import List

#endregion

#region Element Intersects Solid Filter

# Obtain Link Doc.
links = FilteredElementCollector(doc).OfClass(RevitLinkInstance)

Documents = [n.GetLinkDocument() for n in links]

linkDoc = None
linkName = IN[0] #type: ignore

for document in Documents:
	if hasattr(document, "Title"):
		linkName == document.Title
		linkDoc = document
		break

# Get LinkDoc Mass
mass = FilteredElementCollector(linkDoc).OfCategory(BuiltInCategory.OST_Mass).WhereElementIsNotElementType().ToElements()

# Create Geometry Options
opts = Options()
opts.DetailLevel = ViewDetailLevel.Fine

# Iterate Mass
result = []

for element in mass:
# Get Solid of Mass
	geoElem = element.get_Geometry(opts)
	for geoObject in geoElem:
		if geoObject.__class__ == Solid and geoObject.Volume > 0:
			solid = geoObject
			filter = ElementIntersectsSolidFilter(solid)
			elements = FilteredElementCollector(doc).WherePasses(filter).ToElements()
			result.append(elements)
	
OUT = result

#endregion