# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr
from pathlib import Path

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")
clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")

from Autodesk.Revit.DB import *
from System.Windows.Forms import *
from System.Drawing import *
from Autodesk.Revit.UI import TaskDialog, TaskDialogCommonButtons, TaskDialogIcon

try:
    Application.EnableVisualStyles()
except Exception:
    pass

# Edit these paths to point at your own models.
MODEL_PATHS = [
    r"C:\PyNET_Samples\Test1.rvt",
    r"C:\PyNET_Samples\Test2.rvt",
]


class WallCreatorForm(Form):

    def __init__(self):
        super().__init__()
        self.confirmed = False
        self.ConfigureForm()
        self.GenerateLabels()
        self.GenerateButtons()

    def Cancel(self, sender, args):
        self.confirmed = False
        self.Close()

    def Execute(self, sender, args):
        self.confirmed = True
        self.Close()

    def ConfigureForm(self):
        self.Text = "PyNET - Wall Creator Test"
        self.WindowState = FormWindowState.Normal
        self.CenterToScreen()
        self.BringToFront()
        self.TopMost = True
        self.Width = 400
        self.Height = 175
        self.FormBorderStyle = FormBorderStyle.FixedDialog
        self.MaximizeBox = False
        self.MinimizeBox = False

    def GenerateLabels(self):
        lbl = Label()
        lbl.Parent = self
        lbl.Text = "Opens 2 RVT models, creates a wall, saves and closes each."
        lbl.Location = Point(20, 15)
        lbl.Width = 355
        lbl.Height = 40

        self.lbl_status = Label()
        self.lbl_status.Parent = self
        self.lbl_status.Text = ""
        self.lbl_status.Location = Point(20, 90)
        self.lbl_status.Width = 155
        self.lbl_status.Height = 25

    def GenerateButtons(self):
        self.btn_execute = Button()
        self.btn_execute.Parent = self
        self.btn_execute.Text = "Execute"
        self.btn_execute.Location = Point(185, 85)
        self.btn_execute.Width = 90
        self.btn_execute.Click += self.Execute

        btn_cancel = Button()
        btn_cancel.Parent = self
        btn_cancel.Text = "Cancel"
        btn_cancel.Location = Point(283, 85)
        btn_cancel.Width = 90
        btn_cancel.Click += self.Cancel


# Show form (pure UI, no Revit API calls inside message loop)
form = WallCreatorForm()
form.ShowDialog()

if not form.confirmed:
    print("Cancelled by user.")
else:
    # All Revit API work happens here, after ShowDialog returns,
    # still inside the ExternalEventHandler.Execute() context.
    app = __revit__.Application #type:ignore
    errors = []

    for path_str in MODEL_PATHS:
        name = Path(path_str).name
        try:
            model_path = ModelPathUtils.ConvertUserVisiblePathToModelPath(path_str)
            doc = app.OpenDocumentFile(model_path, OpenOptions())

            wall_type = FilteredElementCollector(doc).OfClass(WallType).FirstElement()
            level = (FilteredElementCollector(doc)
                     .OfClass(Level)
                     .WhereElementIsNotElementType()
                     .FirstElement())
            line = Line.CreateBound(XYZ(0, 0, 0), XYZ(10, 0, 0))

            t = Transaction(doc, "PyNET - Create wall")
            t.Start()
            try:
                Wall.Create(doc, line, wall_type.Id, level.Id, 3.0, 0, False, False)
                t.Commit()
            except Exception:
                t.RollBack()
                raise

            doc.Save()
            doc.Close(False)
            print("OK: " + name)

        except Exception as e:
            errors.append(name + ": " + str(e))
            print("ERROR: " + name + " -> " + str(e))

    if errors:
        dlg = TaskDialog("PyNET")
        dlg.TitleAutoPrefix = False
        dlg.MainInstruction = "Finished with errors"
        dlg.MainContent = "Check the Output Window for details."
        dlg.CommonButtons = TaskDialogCommonButtons.Ok
        dlg.MainIcon = TaskDialogIcon.TaskDialogIconWarning
        dlg.Show()
    else:
        dlg = TaskDialog("PyNET")
        dlg.TitleAutoPrefix = False
        dlg.MainInstruction = "Done!"
        dlg.MainContent = "Both models processed correctly."
        dlg.CommonButtons = TaskDialogCommonButtons.Ok
        dlg.MainIcon = TaskDialogIcon.TaskDialogIconInformation
        dlg.Show()
