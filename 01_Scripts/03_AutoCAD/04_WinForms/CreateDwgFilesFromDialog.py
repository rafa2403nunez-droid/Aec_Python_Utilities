# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr
from System import Environment
from pathlib import Path

clr.AddReference("AcMgd")
clr.AddReference("AcCoreMgd")
clr.AddReference("AcDbMgd")
clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")

from Autodesk.AutoCAD.DatabaseServices import (
    Database, OpenMode, BlockTable, BlockTableRecord, Line, DwgVersion
)
from Autodesk.AutoCAD.Geometry import Point3d
from System.Windows.Forms import (
    Form, Label, Button, FormStartPosition,
    MessageBox, MessageBoxButtons, MessageBoxIcon,
)
from System.Drawing import Size, Point, Icon

Civil3DIconPath = (Path.home() / "AppData" / "Roaming" / "Autodesk"
                   / "ApplicationPlugins" / "Raen.Civil3D.Pynet.bundle" / "C3D.ico")


class CreateDwgForm(Form):
    def __init__(self):
        super().__init__()
        self.confirmed = False

        self.Text = "PyNET — Create DWG Files"
        self.Size = Size(420, 220)
        self.StartPosition = FormStartPosition.CenterScreen
        self.FormBorderStyle = self.FormBorderStyle.FixedDialog
        self.MaximizeBox = False
        if Path(str(Civil3DIconPath)).exists():
            self.Icon = Icon(str(Civil3DIconPath))

        lbl = Label()
        lbl.Text = (
            "This will create two DWG files on your Desktop:\n\n"
            "  • PyNET_Test_1.dwg — line from (0,0) to (100,50)\n"
            "  • PyNET_Test_2.dwg — line from (0,0) to (200,100)"
        )
        lbl.Location = Point(20, 20)
        lbl.Size = Size(370, 80)
        self.Controls.Add(lbl)

        btn_run = Button()
        btn_run.Text = "Run"
        btn_run.Size = Size(100, 32)
        btn_run.Location = Point(200, 130)
        btn_run.Click += self.on_run
        self.Controls.Add(btn_run)

        btn_cancel = Button()
        btn_cancel.Text = "Cancel"
        btn_cancel.Size = Size(100, 32)
        btn_cancel.Location = Point(310, 130)
        btn_cancel.Click += self.on_cancel
        self.Controls.Add(btn_cancel)

    def on_run(self, sender, args):
        self.confirmed = True
        self.Close()

    def on_cancel(self, sender, args):
        self.Close()


# ── Entry point ──────────────────────────────────────────────────────────────

form = CreateDwgForm()
form.ShowDialog()

if not form.confirmed:
    print("Cancelled")
else:
    desktop = Path(Environment.GetFolderPath(Environment.SpecialFolder.Desktop))
    saved = []

    for i, filename in enumerate(["PyNET_Test_1.dwg", "PyNET_Test_2.dwg"], 1):
        db = Database(True, True)
        t = db.TransactionManager.StartTransaction()
        try:
            bt = t.GetObject(db.BlockTableId, OpenMode.ForRead)
            ms = t.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForWrite)
            line = Line(Point3d(0, 0, 0), Point3d(i * 100.0, i * 50.0, 0))
            ms.AppendEntity(line)
            t.AddNewlyCreatedDBObject(line, True)
            t.Commit()
        except:
            t.Abort()
            db.Dispose()
            raise

        save_path = str(desktop / filename)
        db.SaveAs(save_path, DwgVersion.Current)
        db.Dispose()
        saved.append(save_path)
        print(f"Saved: {filename}")

    MessageBox.Show(
        "Done!\n\n" + "\n".join(saved),
        "PyNET",
        MessageBoxButtons.OK,
        MessageBoxIcon.Information,
    )

    ia_Result = saved
