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

# endregion

# region Logical And Filter

# Element Is Element Type Filter
elementTypeFilter = ElementIsElementTypeFilter()

# MultiCategoryFilter
categories = [BuiltInCategory.OST_Walls, BuiltInCategory.OST_Doors]
categories = List[BuiltInCategory](categories)
multiCategoryFilter = ElementMulticategoryFilter(categories)

# Logical And Filter
filters = List[ElementFilter]([multiCategoryFilter, elementTypeFilter])
logicalFilter = LogicalAndFilter(filters)

# Collect Elements
collector = FilteredElementCollector(doc).WherePasses(logicalFilter).ToElements()

OUT = collector 

# endregion