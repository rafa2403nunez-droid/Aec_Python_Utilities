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
    networks = []
    for nid in civil_doc.GetPipeNetworkIds():
        n = t.GetObject(nid, OpenMode.ForRead)
        pipes = []
        for pid in n.GetPipeIds():
            p = t.GetObject(pid, OpenMode.ForRead)
            pipes.append(
                {
                    "name": p.Name,
                    "length": round(p.Length3DToInsideEdge, 2),
                    "inner_diameter": round(p.InnerDiameterOrWidth, 3),
                }
            )
        structures = []
        for sid in n.GetStructureIds():
            s = t.GetObject(sid, OpenMode.ForRead)
            structures.append({"name": s.Name, "type": type(s).__name__})
        networks.append(
            {
                "name": n.Name,
                "pipes": pipes,
                "structures": structures,
            }
        )
    t.Commit()
finally:
    t.Dispose()

for net in networks:
    print(f"Network: {net['name']}")
    print(f"  Pipes: {len(net['pipes'])}, Structures: {len(net['structures'])}")
    total_length = sum(p["length"] for p in net["pipes"])
    print(f"  Total pipe length: {round(total_length, 2)} m")

ia_Result = networks
