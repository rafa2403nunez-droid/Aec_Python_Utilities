# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")

from Autodesk.Revit.DB import *

uidoc = __revit__.ActiveUIDocument  #type:ignore
doc = uidoc.Document

LINK_NAME = "LinkedModel"


class ElementIntersectsSolidScript:
    @staticmethod
    def Run(doc, link_name):
        links = FilteredElementCollector(doc).OfClass(RevitLinkInstance)
        linkDoc = None
        for link in links:
            linked = link.GetLinkDocument()
            if hasattr(linked, "Title"):
                linkDoc = linked
                break

        if linkDoc is None:
            print("No linked document found.")
            return []

        mass = FilteredElementCollector(linkDoc).OfCategory(BuiltInCategory.OST_Mass).WhereElementIsNotElementType().ToElements()
        opts = Options()
        opts.DetailLevel = ViewDetailLevel.Fine

        result = []
        for element in mass:
            geoElem = element.get_Geometry(opts)
            for geoObject in geoElem:
                if geoObject.__class__ == Solid and geoObject.Volume > 0:
                    solid = geoObject
                    intersectsFilter = ElementIntersectsSolidFilter(solid)
                    elements = FilteredElementCollector(doc).WherePasses(intersectsFilter).ToElements()
                    result.append(list(elements))

        print(f"Checked {len(list(mass))} mass element(s), found intersecting groups.")
        return result


ElementIntersectsSolidScript.Run(doc, LINK_NAME)
