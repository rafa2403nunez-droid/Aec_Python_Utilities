# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("AcMgd")
clr.AddReference("AcCoreMgd")
clr.AddReference("AcDbMgd")
clr.AddReference("AecBaseMgd")
clr.AddReference("AecPropDataMgd")

from Autodesk.AutoCAD.ApplicationServices import Application as AcadApp
from Autodesk.AutoCAD.DatabaseServices import OpenMode, BlockTable, BlockTableRecord
from Autodesk.Aec.PropertyData.DatabaseServices import (
    PropertyDataServices,
    PropertySetDefinition,
    PropertySet,
)

doc = AcadApp.DocumentManager.MdiActiveDocument
db = doc.Database

t = db.TransactionManager.StartTransaction()
try:
    bt = t.GetObject(db.BlockTableId, OpenMode.ForRead)
    ms = t.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForRead)

    result = []
    for oid in ms:
        obj = t.GetObject(oid, OpenMode.ForRead)
        obj_psets = []
        for pset_def_id in PropertyDataServices.GetPropertySetDefinitionsUsed(obj):
            pset_def = t.GetObject(pset_def_id, OpenMode.ForRead)
            if pset_def is None:
                continue
            pset_id = PropertyDataServices.GetPropertySet(obj, pset_def.Id)
            pset = t.GetObject(pset_id, OpenMode.ForRead)
            if pset is None:
                continue
            props = {}
            for prop_def in pset_def.Definitions:
                val = pset.GetAt(pset.PropertyNameToId(prop_def.Name))
                props[prop_def.Name] = str(val) if val is not None else ""
            obj_psets.append({"set": pset_def.Name, "properties": props})

        if obj_psets:
            result.append(
                {
                    "handle": obj.Handle.ToString(),
                    "type": type(obj).__name__,
                    "property_sets": obj_psets,
                }
            )
    t.Commit()
finally:
    t.Dispose()

print(f"Found {len(result)} objects with property sets")
ia_Result = result
