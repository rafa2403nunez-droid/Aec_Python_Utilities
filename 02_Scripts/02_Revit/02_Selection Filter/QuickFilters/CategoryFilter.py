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

#region Category Filter

# This Category Filter accept a Inverse including true
categoryFilter = ElementCategoryFilter(BuiltInCategory.OST_Walls)
collectorFilter = FilteredElementCollector(doc).WherePasses(categoryFilter).WhereElementIsNotElementType().ToElements()

# Collect Elements without Filter Creation
collectorSimplified = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Walls).WhereElementIsNotElementType().ToElements()

# Show Elements in Revit
ids = List[ElementId]([n.Id for n in collectorSimplified])
uidoc.Selection.SetElementIds(ids)
uidoc.ShowElements(ids)

OUT = collectorFilter, collectorSimplified

#endregion


collector = FilteredElementCollector(doc).WhereElementIsElementType().ToElements()