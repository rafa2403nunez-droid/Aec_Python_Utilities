# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

doc = __revit__.ActiveUIDocument.Document  #type:ignore

PARAM_ORIGIN = "Mark"
PARAM_RESULT = "Comments"
IS_TYPE = False


def transfer_value(doc, name_origin, name_result, category, is_type):
    cat_filter = ElementCategoryFilter(category.Id)
    collector = (FilteredElementCollector(doc).WherePasses(cat_filter)
                 .WhereElementIsElementType() if is_type
                 else FilteredElementCollector(doc).WherePasses(cat_filter)
                 .WhereElementIsNotElementType())
    count = 0
    for elem in collector.ToElements():
        src = elem.LookupParameter(name_origin)
        dst = elem.LookupParameter(name_result)
        if src is None or dst is None or dst.IsReadOnly:
            continue
        if src.StorageType != dst.StorageType:
            continue
        if src.StorageType == StorageType.String and src.HasValue and src.AsString():
            dst.Set(src.AsString())
            count += 1
        elif src.StorageType == StorageType.Integer and src.HasValue:
            dst.Set(src.AsInteger())
            count += 1
        elif src.StorageType == StorageType.Double and src.HasValue:
            dst.SetValueString(src.AsValueString())
            count += 1
    return count


class TransferValueParameterScript:
    @staticmethod
    def Run(doc, param_origin, param_result, is_type):
        model_cats = [c for c in doc.Settings.Categories
                      if c.CategoryType == CategoryType.Model]

        t = Transaction(doc, "PyNET - Transfer Parameter Values")
        t.Start()
        try:
            total = 0
            for cat in model_cats:
                total += transfer_value(doc, param_origin, param_result, cat, is_type)
            t.Commit()
        except:
            t.RollBack()
            raise

        print(f"Transferred '{param_origin}' → '{param_result}' for {total} elements.")


TransferValueParameterScript.Run(doc, PARAM_ORIGIN, PARAM_RESULT, IS_TYPE)
