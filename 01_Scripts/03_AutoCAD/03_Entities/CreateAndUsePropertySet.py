# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("AcMgd")
clr.AddReference("AcCoreMgd")
clr.AddReference("AcDbMgd")
clr.AddReference("AecBaseMgd")
clr.AddReference("AecPropDataMgd")

from Autodesk.AutoCAD.ApplicationServices import Application as AcadApp
from Autodesk.AutoCAD.DatabaseServices import OpenMode, DBDictionary, BlockTable, BlockTableRecord
from Autodesk.Aec.PropertyData.DatabaseServices import (
    PropertySetDefinition,
    PropertyDefinition,
    PropertyDataServices,
    PropertySet,
)
from Autodesk.Aec.PropertyData import DataType

doc = AcadApp.DocumentManager.MdiActiveDocument
db = doc.Database

PSET_NAME = "PYNET_TEST_PSET"
NOD_PSET_KEY = "AEC_PROPERTY_SET_DEFS"

# ── 1. Create PropertySetDefinition ─────────────────────────────────────────
lock = doc.LockDocument()
try:
    t = db.TransactionManager.StartTransaction()
    try:
        nod = t.GetObject(db.NamedObjectsDictionaryId, OpenMode.ForRead)
        pset_dict = t.GetObject(nod[NOD_PSET_KEY], OpenMode.ForWrite)

        if not pset_dict.Contains(PSET_NAME):
            pset_def = PropertySetDefinition()
            pset_def.SetToStandard(db)
            pset_def.SubSetDatabaseDefaults(db)
            pset_def.Description = "Property set created by PyNET"
            pset_def.AppliesToAll = True

            for name, dtype, default in [
                ("Site", DataType.Text, ""),
                ("Code", DataType.Text, ""),
                ("Quantity", DataType.Real, 0.0),
            ]:
                pd = PropertyDefinition()
                pd.SetToStandard(db)
                pd.SubSetDatabaseDefaults(db)
                pd.Name = name
                pd.DataType = dtype
                pd.DefaultData = default
                pset_def.Definitions.Add(pd)

            pset_dict.SetAt(PSET_NAME, pset_def)
            t.AddNewlyCreatedDBObject(pset_def, True)
            print(f"Created PropertySetDefinition: {PSET_NAME}")
        else:
            print(f"PropertySetDefinition already exists: {PSET_NAME}")

        t.Commit()
    except:
        t.Abort()
        raise
finally:
    lock.Dispose()

# ── 2. Attach to an entity and write values ──────────────────────────────────
lock = doc.LockDocument()
try:
    t = db.TransactionManager.StartTransaction()
    try:
        nod = t.GetObject(db.NamedObjectsDictionaryId, OpenMode.ForRead)
        pset_dict = t.GetObject(nod[NOD_PSET_KEY], OpenMode.ForRead)
        pset_def = t.GetObject(pset_dict.GetAt(PSET_NAME), OpenMode.ForRead)

        bt = t.GetObject(db.BlockTableId, OpenMode.ForRead)
        ms = t.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForRead)

        # Attach to the first entity
        for oid in ms:
            entity = t.GetObject(oid, OpenMode.ForWrite)
            break

        PropertyDataServices.AddPropertySet(entity, pset_def.Id)
        pset_id = PropertyDataServices.GetPropertySet(entity, pset_def.Id)
        pset = t.GetObject(pset_id, OpenMode.ForWrite)

        pset.SetAt(pset.PropertyNameToId("Site"), "OBRA_001")
        pset.SetAt(pset.PropertyNameToId("Code"), "PYN-TEST")
        pset.SetAt(pset.PropertyNameToId("Quantity"), 42.5)

        print(f"Attached and wrote values to {type(entity).__name__} (handle {entity.Handle})")
        t.Commit()
    except:
        t.Abort()
        raise
finally:
    lock.Dispose()

# ── 3. Read values back ──────────────────────────────────────────────────────
t = db.TransactionManager.StartTransaction()
try:
    nod = t.GetObject(db.NamedObjectsDictionaryId, OpenMode.ForRead)
    pset_dict = t.GetObject(nod[NOD_PSET_KEY], OpenMode.ForRead)
    pset_def = t.GetObject(pset_dict.GetAt(PSET_NAME), OpenMode.ForRead)

    bt = t.GetObject(db.BlockTableId, OpenMode.ForRead)
    ms = t.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForRead)

    for oid in ms:
        entity = t.GetObject(oid, OpenMode.ForRead)
        pset_id = PropertyDataServices.GetPropertySet(entity, pset_def.Id)
        if pset_id.IsNull:
            continue
        pset = t.GetObject(pset_id, OpenMode.ForRead)
        values = {d.Name: str(pset.GetAt(pset.PropertyNameToId(d.Name))) for d in pset_def.Definitions}
        print(f"Read values from {type(entity).__name__}: {values}")
        break

    t.Commit()
finally:
    t.Dispose()
