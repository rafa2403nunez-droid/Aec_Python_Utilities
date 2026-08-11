# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

doc = __revit__.ActiveUIDocument.Document  #type:ignore

LINK_NAME = ""       # name of the linked document (leave empty to use first found)
PARAM_NAME = ""      # parameter to set on intersecting elements
SPECIAL_VALUE = ""   # value to use when element intersects multiple solids


class SetParamContainedInSolidScript:
    @staticmethod
    def get_link_doc(doc, link_name):
        for inst in FilteredElementCollector(doc).OfClass(RevitLinkInstance):
            linked = inst.GetLinkDocument()
            if linked is not None and (not link_name or linked.Title == link_name):
                return linked
        return None

    @staticmethod
    def set_params(doc, mass_elements, param_name, special_value, options):
        updated = 0
        previous_element_sets = []
        for mass in mass_elements:
            geo_elem = mass.get_Geometry(options)
            for geo_obj in geo_elem:
                if not isinstance(geo_obj, Solid) or geo_obj.Volume <= 0:
                    continue
                solid_filter = ElementIntersectsSolidFilter(geo_obj)
                intersecting = list(FilteredElementCollector(doc)
                                    .WherePasses(solid_filter).ToElements())
                mass_param = mass.LookupParameter(param_name)
                mass_value = mass_param.AsString() if mass_param else ""
                for elem in intersecting:
                    ep = elem.LookupParameter(param_name)
                    if ep is None or ep.IsReadOnly:
                        continue
                    already_seen = any(elem.Id in prev for prev in previous_element_sets)
                    ep.Set(special_value if already_seen else mass_value)
                    updated += 1
                previous_element_sets.append([e.Id for e in intersecting])
        return updated

    @staticmethod
    def Run(doc, link_name, param_name, special_value):
        link_doc = SetParamContainedInSolidScript.get_link_doc(doc, link_name)
        if link_doc is None:
            print("Linked document not found.")
            return

        mass = (FilteredElementCollector(link_doc)
                .OfCategory(BuiltInCategory.OST_Mass)
                .WhereElementIsNotElementType().ToElements())
        opts = Options()
        opts.DetailLevel = ViewDetailLevel.Fine

        t = Transaction(doc, "PyNET - Set Parameter Contained in Solid")
        t.Start()
        try:
            count = SetParamContainedInSolidScript.set_params(
                doc, mass, param_name, special_value, opts)
            t.Commit()
        except:
            t.RollBack()
            raise

        print(f"Updated {count} element parameters.")


SetParamContainedInSolidScript.Run(doc, LINK_NAME, PARAM_NAME, SPECIAL_VALUE)
