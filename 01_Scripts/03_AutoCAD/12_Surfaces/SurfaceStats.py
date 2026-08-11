# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("AcMgd")
clr.AddReference("AcCoreMgd")
clr.AddReference("AcDbMgd")
clr.AddReference("AecBaseMgd")
clr.AddReference("AeccDbMgd")

from Autodesk.AutoCAD.ApplicationServices import Application as AcadApp
from Autodesk.AutoCAD.DatabaseServices import OpenMode
from Autodesk.Civil.ApplicationServices import CivilApplication

doc = AcadApp.DocumentManager.MdiActiveDocument
db = doc.Database
civil_doc = CivilApplication.ActiveDocument

t = db.TransactionManager.StartTransaction()
try:
    surfaces = []
    for sid in civil_doc.GetSurfaceIds():
        s = t.GetObject(sid, OpenMode.ForRead)
        stats = s.GetGeneralProperties()
        surfaces.append(
            {
                "name": s.Name,
                "type": type(s).__name__,
                "min_elev": round(stats.MinimumElevation, 3),
                "max_elev": round(stats.MaximumElevation, 3),
                "mean_elev": round(stats.MeanElevation, 3),
                "num_points": stats.NumberOfPoints,
                "extents": {
                    "min_x": round(stats.MinimumCoordinateX, 2),
                    "min_y": round(stats.MinimumCoordinateY, 2),
                    "max_x": round(stats.MaximumCoordinateX, 2),
                    "max_y": round(stats.MaximumCoordinateY, 2),
                },
            }
        )
    t.Commit()
finally:
    t.Dispose()

for s in surfaces:
    print(f"{s['name']} ({s['type']})")
    print(f"  Elevation: {s['min_elev']} – {s['max_elev']} m  (mean {s['mean_elev']})")
    print(f"  Points: {s['num_points']}")

ia_Result = surfaces
