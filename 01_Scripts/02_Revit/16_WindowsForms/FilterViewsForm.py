# SPDX-License-Identifier: MIT
# Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import clr

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")
clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")

from Autodesk.Revit.DB import *
from System.Windows.Forms import *
from System.Drawing import *
from Autodesk.Revit.UI import TaskDialog, TaskDialogCommonButtons, TaskDialogIcon  # noqa: F401

try:
    Application.EnableVisualStyles()
except Exception:
    pass

doc = __revit__.ActiveUIDocument.Document  #type:ignore


class FilterViewsForm(Form):
    def __init__(self, param_names):
        super().__init__()
        self.selected_param = None
        self.filter_value = None
        self.result_views = []
        self.confirmed = False
        self._build_ui(param_names)

    def _build_ui(self, param_names):
        self.Text = "PyNET - Filter Views by Parameter"
        self.Width = 420
        self.Height = 260
        self.FormBorderStyle = FormBorderStyle.FixedDialog
        self.MaximizeBox = False
        self.CenterToScreen()
        self.BringToFront()
        self.TopMost = True

        lbl1 = Label()
        lbl1.Parent = self
        lbl1.Text = "Select project parameter to filter 3D views:"
        lbl1.Location = Point(20, 15)
        lbl1.Width = 360
        lbl1.Height = 22

        self.cb_param = ComboBox()
        self.cb_param.Parent = self
        self.cb_param.Location = Point(20, 40)
        self.cb_param.Width = 360
        self.cb_param.DropDownStyle = ComboBoxStyle.DropDownList
        for name in param_names:
            self.cb_param.Items.Add(name)
        if self.cb_param.Items.Count > 0:
            self.cb_param.SelectedIndex = 0
        self.cb_param.SelectedIndexChanged += self._on_param_select

        lbl2 = Label()
        lbl2.Parent = self
        lbl2.Text = "Parameter value to match:"
        lbl2.Location = Point(20, 80)
        lbl2.Width = 360
        lbl2.Height = 22

        self.tb_value = TextBox()
        self.tb_value.Parent = self
        self.tb_value.Location = Point(20, 105)
        self.tb_value.Width = 360
        self.tb_value.TextChanged += self._on_value_change

        btn_filter = Button()
        btn_filter.Parent = self
        btn_filter.Text = "Filter"
        btn_filter.Location = Point(290, 155)
        btn_filter.Width = 90
        btn_filter.Click += self._on_filter

        btn_cancel = Button()
        btn_cancel.Parent = self
        btn_cancel.Text = "Cancel"
        btn_cancel.Location = Point(190, 155)
        btn_cancel.Width = 90
        btn_cancel.Click += self._on_cancel

        self.lbl_result = Label()
        self.lbl_result.Parent = self
        self.lbl_result.Text = ""
        self.lbl_result.Location = Point(20, 160)
        self.lbl_result.Width = 160
        self.lbl_result.Height = 22

    def _on_param_select(self, sender, _args):
        self.selected_param = sender.SelectedItem

    def _on_value_change(self, sender, _args):
        self.filter_value = sender.Text

    def _on_filter(self, _sender, _args):
        self.confirmed = True
        self.Close()

    def _on_cancel(self, _sender, _args):
        self.confirmed = False
        self.Close()


class FilterViewsScript:
    @staticmethod
    def get_param_names(doc):
        names = []
        iterator = doc.ParameterBindings.ForwardIterator()
        while iterator.MoveNext():
            names.append(iterator.Key.Name)
        return sorted(names)

    @staticmethod
    def filter_views(doc, param_name, value):
        iterator = doc.ParameterBindings.ForwardIterator()
        provider = None
        while iterator.MoveNext():
            if iterator.Key.Name == param_name:
                provider = ParameterValueProvider(iterator.Key.Id)
                break

        if provider is None:
            return []

        rule = FilterStringRule(provider, FilterStringEquals(), value, True)
        elem_filter = ElementParameterFilter(rule)
        views = (FilteredElementCollector(doc)
                 .OfClass(View3D)
                 .WherePasses(elem_filter).ToElements())
        return [v.Name for v in views]

    @staticmethod
    def Run(doc):
        param_names = FilterViewsScript.get_param_names(doc)
        if not param_names:
            print("No project parameters found.")
            return

        form = FilterViewsForm(param_names)
        form.ShowDialog()

        if not form.confirmed:
            print("Cancelled.")
            return

        if not form.selected_param or not form.filter_value:
            print("No parameter or value specified.")
            return

        view_names = FilterViewsScript.filter_views(doc, form.selected_param, form.filter_value)

        if not view_names:
            print(f"No 3D views found with '{form.selected_param}' = '{form.filter_value}'.")
            return

        print(f"Parameter: {form.selected_param}  |  Value: {form.filter_value}")
        print(f"Filtered views ({len(view_names)}):")
        for name in view_names:
            print(f"  {name}")


FilterViewsScript.Run(doc)
