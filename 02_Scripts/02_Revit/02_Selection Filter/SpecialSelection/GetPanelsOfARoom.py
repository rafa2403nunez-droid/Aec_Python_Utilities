#region References

# Load the Python Standard and DesignScript Libraries
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

# region Get panels of a Room

# Rooms Input
rooms = UnwrapElement(IN[0]) #type: ignore

# Curtain Panels Input
panels = UnwrapElement(IN[1]) #type: ignore

# Tolerance Input
tolerance = IN[2] #type: ignore

# Create def Convert Tolerance to Internal Units
def convertToMeters(value):
	result = UnitUtils.ConvertToInternalUnits(value, UnitTypeId.Meters) #type: ignore
	return result

def GetPanelsOfARoom(rooms, panels, tolerance):
# Create Geometry Options
    opts = Options()
    opts.DetailLevel = ViewDetailLevel.Fine
# Create Empty List where append the Result
    collectionRoomsPanels = []
#Iterate Rooms and Create a List for each Room
    for room in rooms:
        panelsResult = []
#Iterate Panels and Get the Geometry of the Element
        for panel in panels:
            geoElem = panel.get_Geometry(opts)
#Get Solids of the Geometry of the Element
            for geoObject in geoElem:
                geoInstances = geoObject.GetInstanceGeometry()
#Iterate Solids and desprise the solid with Volune less than a Tolerance. Obtain Centroid
                for instance in geoInstances:
                    if instance.__class__ == Solid and instance.Volume > 0.1:
                        centroid = instance.ComputeCentroid()
# Determinate Solid Orientation. Obtains Normal Points
                        if panel.HandOrientation.IsAlmostEqualTo(XYZ(1, 0, 0)) or panel.HandOrientation.IsAlmostEqualTo(XYZ(-1, 0, 0)):
                            p1 = XYZ(centroid.X, centroid.Y + convertToMeters(tolerance), centroid.Z)
                            p2 = XYZ(centroid.X, centroid.Y - convertToMeters(tolerance), centroid.Z)
                        if panel.HandOrientation.IsAlmostEqualTo(XYZ(0, 1, 0)) or panel.HandOrientation.IsAlmostEqualTo(XYZ(0, -1, 0)):
                            p1 = XYZ(centroid.X + convertToMeters(tolerance), centroid.Y, centroid.Z)
                            p2 = XYZ(centroid.X - convertToMeters(tolerance), centroid.Y, centroid.Z)
                        if panel.HandOrientation.X < 0 and panel.HandOrientation.Y > 0: 
                            p1 = XYZ(centroid.X + convertToMeters(tolerance), centroid.Y + convertToMeters(tolerance), centroid.Z)
                            p2 = XYZ(centroid.X - convertToMeters(tolerance), centroid.Y - convertToMeters(tolerance), centroid.Z)
                        if panel.HandOrientation.X < 0 and panel.HandOrientation.Y < 0: 
                            p1 = XYZ(centroid.X - convertToMeters(tolerance), centroid.Y + convertToMeters(tolerance), centroid.Z)
                            p2 = XYZ(centroid.X + convertToMeters(tolerance), centroid.Y - convertToMeters(tolerance), centroid.Z)
                        if panel.HandOrientation.X > 0 and panel.HandOrientation.Y > 0: 
                            p1 = XYZ(centroid.X + convertToMeters(tolerance), centroid.Y - convertToMeters(tolerance), centroid.Z)
                            p2 = XYZ(centroid.X - convertToMeters(tolerance), centroid.Y + convertToMeters(tolerance), centroid.Z)
                        if panel.HandOrientation.X > 0 and panel.HandOrientation.Y < 0: 
                            p1 = XYZ(centroid.X + convertToMeters(tolerance), centroid.Y + convertToMeters(tolerance), centroid.Z)
                            p2 = XYZ(centroid.X - convertToMeters(tolerance), centroid.Y - convertToMeters(tolerance), centroid.Z)
                        else:
                            pass
# Determinate if the Normal Points are contained in the Room. Append Room and Panel if it is True
                        if room.IsPointInRoom(p1) or room.IsPointInRoom(p2):
                            if panelsResult.Contains(room):
                                pass
                            else:
                                panelsResult.append(room)
                            panelsResult.append(panel)
                        else:
                            pass
# Append list with Room and Panels To Restult List
        collectionRoomsPanels.append(panelsResult)
# Clean Empty Lists
    result = [x for x in collectionRoomsPanels if x !=[]]
    return result

# Generate Output 
OUT =  GetPanelsOfARoom(rooms, panels, tolerance)

#endregion
