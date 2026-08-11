# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr
from pathlib import Path

clr.AddReference("AcMgd")
clr.AddReference("AcCoreMgd")
clr.AddReference("AcDbMgd")
clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")

from Autodesk.AutoCAD.ApplicationServices import Application as AcadApp, DocumentCollectionExtension
from Autodesk.AutoCAD.DatabaseServices import (
    Database, OpenMode, BlockTableRecord, Line, DwgVersion, FileOpenMode
)
from Autodesk.AutoCAD.Geometry import Point3d
from System.Windows.Forms import (
    Form, Label, Button, FormStartPosition,
    MessageBox, MessageBoxButtons, MessageBoxIcon,
)
from System.Drawing import Size, Point, Icon

Civil3DIconPath = (Path.home() / "AppData" / "Roaming" / "Autodesk"
                   / "ApplicationPlugins" / "Raen.Civil3D.Pynet.bundle" / "C3D.ico")

# Edit these paths to point at your own drawings.
FILES = [
    Path(r"C:\PyNET_Samples\PyNET_Test_1.dwg"),
    Path(r"C:\PyNET_Samples\PyNET_Test_2.dwg"),
]


class EditDwgForm(Form):
    def __init__(self):
        super().__init__()
        self.confirmed = False
        self.Text = "PyNET — Edit DWG Files"
        self.Size = Size(440, 230)
        self.StartPosition = FormStartPosition.CenterScreen
        self.FormBorderStyle = self.FormBorderStyle.FixedDialog
        self.MaximizeBox = False
        if Path(str(Civil3DIconPath)).exists():
            self.Icon = Icon(str(Civil3DIconPath))

        lbl = Label()
        lbl.Text = (
            "Will open the following files from the Desktop,\n"
            "draw a line in each one and save:\n\n"
            "  • PyNET_Test_1.dwg — new line from (0,0) to (50,200)\n"
            "  • PyNET_Test_2.dwg — new line from (0,0) to (150,300)"
        )
        lbl.Location = Point(20, 20)
        lbl.Size = Size(400, 90)
        self.Controls.Add(lbl)

        btn_run = Button()
        btn_run.Text = "Run"
        btn_run.Size = Size(100, 32)
        btn_run.Location = Point(215, 148)
        btn_run.Click += self.on_run
        self.Controls.Add(btn_run)

        btn_cancel = Button()
        btn_cancel.Text = "Cancel"
        btn_cancel.Size = Size(100, 32)
        btn_cancel.Location = Point(325, 148)
        btn_cancel.Click += self.on_cancel
        self.Controls.Add(btn_cancel)

    def on_run(self, sender, args):
        self.confirmed = True
        self.Close()

    def on_cancel(self, sender, args):
        self.Close()


# ── Show form — no API calls in handlers ─────────────────────────────────────
form = EditDwgForm()
form.ShowDialog()

if not form.confirmed:
    print("Cancelled")
    ia_Result = []
else:
    new_lines = [
        (Point3d(0, 0, 0), Point3d(50.0, 200.0, 0)),
        (Point3d(0, 0, 0), Point3d(150.0, 300.0, 0)),
    ]

    results = []
    for file_path, (start, end) in zip(FILES, new_lines):

        # Open file through DocumentManager — becomes visible/active in AutoCAD UI
        file_doc = DocumentCollectionExtension.Open(
            AcadApp.DocumentManager, str(file_path), False, ""
        )
        db = file_doc.Database

        lock = file_doc.LockDocument()
        try:
            t = db.TransactionManager.StartTransaction()
            try:
                bt = t.GetObject(db.BlockTableId, OpenMode.ForRead)
                ms = t.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForWrite)
                ln = Line(start, end)
                ms.AppendEntity(ln)
                t.AddNewlyCreatedDBObject(ln, True)
                t.Commit()
            except:
                t.Abort()
                raise
        finally:
            lock.Dispose()

        # C# pattern: UpgradeDocOpen + SaveAs on the active document
        file_doc.UpgradeDocOpen()
        db.SaveAs(file_doc.Name, True, DwgVersion.Current, None)

        print(f"Updated: {file_path.name}")
        results.append({"file": file_path.name, "status": "ok", "line_end": f"({end.X},{end.Y})"})

    MessageBox.Show(
        "Done!\n\n" + "\n".join(f"  {r['file']} — {r['status']}" for r in results),
        "PyNET",
        MessageBoxButtons.OK,
        MessageBoxIcon.Information,
    )

    ia_Result = results
