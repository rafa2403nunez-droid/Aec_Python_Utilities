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

#region Element Parameter Filter. BuiltInParameter Parameter

# Create Evaluation Rule
provider = ParameterValueProvider(ElementId(BuiltInParameter.ROOM_AREA))
evaluator = FilterNumericGreater()
value = UnitUtils.ConvertToInternalUnits(10, UnitTypeId.Meters) #type: ignore
rule = FilterDoubleRule(provider, evaluator, value, 0.001)

# Create Filter
filter = ElementParameterFilter(rule)

# Collect Elements
collectorNativeParamater = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).WherePasses(filter).ToElements()

#endregion

#region Element Parameter Filter. Project Parameter

# Get Project parameter
iterator = doc.ParameterBindings.ForwardIterator()
iterator.Reset()
provider = None
while iterator.MoveNext():
    name = iterator.Key.Name
    if name == "parameter_01":
        provider = ParameterValueProvider(iterator.Key.Id)
        break

# Create Evaluation Rule
evaluator = FilterStringEquals()
value = "Revit API"
rule = FilterStringRule(provider, evaluator, value, True)

# Create Filter
filter = ElementParameterFilter(rule)

# Collect Elements
collectorProjectParameter = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).WherePasses(filter).ToElements()

OUT = collectorNativeParamater, collectorProjectParameter

#endregion
