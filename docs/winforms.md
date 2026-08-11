<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform -->

# Guide: Windows Forms (Revit, AutoCAD & Civil 3D)

Read this guide **before writing any script that shows a form, dialog, or custom UI**. These rules are hard-won; ignoring them causes crashes or silent context loss.

Related: [revit.md](revit.md) · [autocad-civil.md](autocad-civil.md)

---

## Core rules (all hosts)

### Import order — critical

`System.Windows.Forms` has its own `TaskDialog` (.NET 6+). If `from System.Windows.Forms import *` runs **after** the Revit UI import, the WinForms `TaskDialog` silently overwrites the Revit one. **Always import WinForms before Revit UI:**

```python
from Autodesk.Revit.DB import *
from System.Windows.Forms import *      # WinForms first
from System.Drawing import *
from Autodesk.Revit.UI import TaskDialog, TaskDialogCommonButtons, TaskDialogIcon  # Revit UI last — wins
```

### super().__init__() is mandatory

Python.NET 3.x requires explicit `super().__init__()` as the first line of any class inheriting from a .NET type. Without it, accessing `.Text`, `.Location`, etc. crashes with `NullReferenceException`.

```python
class MyForm(Form):
    def __init__(self):
        super().__init__()   # MANDATORY — must be first
        self.Text = "Title"
```

### EnableVisualStyles / SetCompatibleTextRenderingDefault

The host already created Win32 windows, so these may throw. Wrap in try/except and never call `SetCompatibleTextRenderingDefault`:

```python
try:
    Application.EnableVisualStyles()
except Exception:
    pass
# Never call Application.SetCompatibleTextRenderingDefault() — always throws in the host
```

### No host API calls inside form event handlers

Scripts run inside `IExternalEventHandler.Execute()` (Revit) / a command context (AutoCAD). When `form.ShowDialog()` starts the WinForms message loop, the host context is ambiguous. **Any host API call inside a button click handler will fail or crash.**

**Pattern: form is UI-only; all API work happens after `ShowDialog()` returns.**

```python
class MyForm(Form):
    def __init__(self):
        super().__init__()
        self.confirmed = False
        # ... build UI

    def OnExecute(self, sender, args):
        self.confirmed = True
        self.Close()   # just close — no API calls here

    def OnCancel(self, sender, args):
        self.Close()

form = MyForm()
form.ShowDialog()

if form.confirmed:
    # All host API work here — still inside ExternalEventHandler.Execute()
    ...
```

### No Application.DoEvents()

`Application.DoEvents()` inside an ExternalEventHandler causes re-entrancy and crashes. Never use it.

---

## Revit TaskDialog — string hell

`Autodesk.Revit.UI.TaskDialog` is painful with Python.NET 3.x.

**Use plain Python `str` — never `System.String(...)`.** `System.String` has no string constructor, so `System.String("PyNET")` throws "No method matches". Plain `str` is auto-converted.

```python
# WRONG
dlg = TaskDialog(System.String("PyNET"))
dlg.MainInstruction = System.String("Done!")

# CORRECT
dlg = TaskDialog("PyNET")
dlg.MainInstruction = "Done!"
```

Full working pattern:

```python
from Autodesk.Revit.DB import *
from System.Windows.Forms import *
from System.Drawing import *
from Autodesk.Revit.UI import TaskDialog, TaskDialogCommonButtons, TaskDialogIcon

dlg = TaskDialog("PyNET")
dlg.TitleAutoPrefix = False
dlg.MainInstruction = "Done!"
dlg.MainContent = "Both models processed correctly."
dlg.CommonButtons = TaskDialogCommonButtons.Ok
dlg.MainIcon = TaskDialogIcon.TaskDialogIconInformation
dlg.Show()
```

---

## AutoCAD / Civil 3D specifics

The same core rules apply. For opening and saving external DWG files from a form, see the two validated patterns (Background / UI) in [autocad-civil.md](autocad-civil.md).

---

## Navisworks form icon — standard path

Forms shown in Navisworks should carry the PyNET bundle icon. The **standard location** is the
bundle root (no longer `Contents/2024/Images/`):

```python
from System.Drawing import Icon

NavisworksIconPath = (Path.home() / "AppData" / "Roaming" / "Autodesk"
                      / "ApplicationPlugins" / "Raen.Navisworks.Pynet.bundle" / "manage.ico")

class MyForm(Form):
    def __init__(self):
        super().__init__()
        if Path(str(NavisworksIconPath)).exists():   # guard — never crash if missing
            self.Icon = Icon(str(NavisworksIconPath))
```

Always guard with `.exists()` so a missing icon degrades gracefully instead of throwing. Note the
bundle folder name casing is `Raen.Navisworks.Pynet.bundle`.

---

## AutoCAD / Civil 3D form icon — standard path

Same principle as Navisworks. The Civil 3D bundle ships its own icon (`C3D.ico`) at the bundle root:

```python
from System.Drawing import Icon

Civil3DIconPath = (Path.home() / "AppData" / "Roaming" / "Autodesk"
                   / "ApplicationPlugins" / "Raen.Civil3D.Pynet.bundle" / "C3D.ico")

class MyForm(Form):
    def __init__(self):
        super().__init__()
        # ... Text, Size, StartPosition, etc.
        if Path(str(Civil3DIconPath)).exists():   # guard — never crash if missing
            self.Icon = Icon(str(Civil3DIconPath))
```

The four reference forms below all apply this icon. Bundle folder casing: `Raen.Civil3D.Pynet.bundle`.

---

## Reference scripts

- `01_Scripts/02_Revit/16_WindowsForms/OpenModelsCreateWallTest.py` — Revit: confirmation form, full API work after ShowDialog, TaskDialog result.
- `01_Scripts/03_AutoCAD/04_WinForms/EditDwg_Background.py` — AutoCAD Pattern A.
- `01_Scripts/03_AutoCAD/04_WinForms/EditDwg_WithUI.py` — AutoCAD Pattern B.
