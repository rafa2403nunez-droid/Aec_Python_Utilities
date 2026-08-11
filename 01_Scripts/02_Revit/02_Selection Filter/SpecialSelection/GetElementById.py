# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Drawing')

from Autodesk.Revit.DB import ElementId
from System.Windows.Forms import (Form, Label, TextBox, Button, DialogResult,
                                   MessageBox, MessageBoxButtons, MessageBoxIcon,
                                   FormStartPosition, BorderStyle)
from System.Drawing import Size, Point, Font, FontStyle
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document


def get_element_id(raw_id):
    try:
        return ElementId(int(raw_id))
    except Exception:
        return None


class GetByIdForm(Form):
    def __init__(self):
        self.Text = "Get Element by ID"
        self.Size = Size(320, 150)
        self.StartPosition = FormStartPosition.CenterScreen
        self.FormBorderStyle = BorderStyle.FixedDialog
        self.MaximizeBox = False

        lbl = Label()
        lbl.Text = "Element ID:"
        lbl.Location = Point(12, 18)
        lbl.Size = Size(80, 20)

        self.txt = TextBox()
        self.txt.Location = Point(95, 15)
        self.txt.Size = Size(195, 22)

        btn = Button()
        btn.Text = "Select"
        btn.Location = Point(95, 55)
        btn.Size = Size(90, 28)
        btn.Click += self.on_select

        self.Controls.Add(lbl)
        self.Controls.Add(self.txt)
        self.Controls.Add(btn)

    def on_select(self, sender, args):
        self.DialogResult = DialogResult.OK
        self.Close()


form = GetByIdForm()
if form.ShowDialog() == DialogResult.OK:
    raw = form.txt.Text.strip()
    eid = get_element_id(raw)

    if eid is None:
        MessageBox.Show("Invalid ID: " + raw, "Error", MessageBoxButtons.OK, MessageBoxIcon.Error)
    else:
        elem = doc.GetElement(eid)
        if elem is None:
            MessageBox.Show("No element found with ID " + raw, "Not Found",
                            MessageBoxButtons.OK, MessageBoxIcon.Warning)
        else:
            ids = List[ElementId]()
            ids.Add(eid)
            uidoc.Selection.SetElementIds(ids)
            uidoc.ShowElements(ids)
            print(f"Selected: [{raw}] {elem.GetType().Name} — {elem.Name if hasattr(elem, 'Name') else ''}")
