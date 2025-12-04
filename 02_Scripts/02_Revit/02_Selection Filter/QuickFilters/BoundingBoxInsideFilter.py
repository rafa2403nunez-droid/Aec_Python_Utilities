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

#region Bounding Box Inside Filter Filter

# Create a OutLine
value = UnitUtils.ConvertFromInternalUnits(10, UnitTypeId.Meters) #type: ignore
point = XYZ(0, 0, 0)
outline = Outline(point, XYZ(value, value, value))

# This Filter accept a Inverse including true. This filter collects the elements that are in a BoundingBox. Elements that are Partialy in the BoundingBox are not included
boundingBoxInsidefilter = BoundingBoxIsInsideFilter(outline)
collectorFilter = FilteredElementCollector(doc).WherePasses(boundingBoxInsidefilter).ToElements()

# Show Elements in Revit
ids = List[ElementId]([n.Id for n in collectorFilter])
uidoc.Selection.SetElementIds(ids)
uidoc.ShowElements(ids)

OUT = collectorFilter

#endregion