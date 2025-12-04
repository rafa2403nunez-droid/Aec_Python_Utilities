#region References

# Load the Python Standard and DesignScript Libraries
from gc import collect
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
from Autodesk.Revit.UI.Selection import *

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

#region Family Symbol Filter
reference = None
try:
    reference = uidoc.Selection.PickObject(ObjectType.Element, "Select a Family Instance (Load Family): ")
except:
    TaskDialog.Show("Revit API", "Operation Cancelled")

# Get Element
element = None
if reference != None:
    element = doc.GetElement(reference)
# Determinate if Element is Family Instance
    if element.__class__ == FamilyInstance:
        familyId = element.Symbol.Family.Id
        # Create Filter
        familySymbolFilter = FamilySymbolFilter(familyId)
        collector = FilteredElementCollector(doc).WherePasses(familySymbolFilter).ToElements()
        OUT = collector
    else:
        OUT = "Element is not Family Instance."   
else:
    OUT = "Refence is Null"

#endregion
