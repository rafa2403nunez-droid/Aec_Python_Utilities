<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform -->

# Guide: Revit scripts

Read this guide **before writing any Revit script**. For element queries/measurements, also read [RevitApiPatterns](../.claude/commands/RevitApiPatterns.md). For forms/dialogs read [winforms.md](winforms.md).

Related: [navisworks.md](navisworks.md) · [autocad-civil.md](autocad-civil.md) · [excel-mcp.md](excel-mcp.md)

---

## Standard boilerplate

The plugin injects a `__revit__` global. **Do not use `Application` from the Navisworks namespace — it does not exist in Revit.**

```python
import clr
import System
from System import Enum, Environment
from pathlib import Path

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

# __revit__ is injected by the plugin — always use this to get the document
doc = __revit__.ActiveUIDocument.Document
```

| | Navisworks | Revit |
|---|---|---|
| Document | `Application.ActiveDocument` | `__revit__.ActiveUIDocument.Document` |
| Main assembly | `Autodesk.Navisworks.Api` | `RevitAPI` |
| UI access | `Application` | `__revit__.ActiveUIDocument` |
| Writes need transaction | No | **Yes** |

---

## Transactions (required for any write)

```python
t = Transaction(doc, "Transaction name")
t.Start()
try:
    # ... write operations ...
    t.Commit()
except:
    t.RollBack()
    raise
```

## Special folder paths

Never hardcode `Path.home() / "Desktop"` — it fails when OneDrive redirects the Desktop. Use .NET:

```python
from System import Environment
desktop = Environment.GetFolderPath(Environment.SpecialFolder.Desktop)
out_path = Path(desktop) / "output.csv"
```

## Iterating BuiltInCategory

```python
from System import Enum
from Autodesk.Revit.DB import BuiltInCategory

for bic in Enum.GetValues(BuiltInCategory):
    if int(bic) >= 0:
        continue  # skip non-negative (invalid) values
    cat = doc.Settings.Categories.get_Item(bic)
    if cat is not None and str(cat.CategoryType) == "Model":
        ...
```

---

## Python.NET runtime contamination (critical)

The Python runtime inside Revit is **persistent and shared** across all executions (both `send_command` and button). A failed import can leave a broken module in `sys.modules` that affects every subsequent script in the session.

### Never modify imports to diagnose an environment error

The standard boilerplate (`clr.AddReference("RevitAPI")` + `from Autodesk.Revit.DB import *`) is correct and matches all working scripts. Changing it to specific imports causes real import errors (`ParameterType`, `BuiltInParameterGroup` do not exist in Revit 2025+) and contaminates the runtime.

### Diagnosis flow for button execution errors

1. **Does the same script work via `send_command`?** If yes, the script is correct.
2. **Is it a .NET assembly load failure** (e.g. `DesktopConnectorInterop`, `AcWebServices`)? That is an environment/session issue, not a script issue.
3. **Do not touch imports.** Tell the user the session is contaminated and ask them to restart Revit.

### Known: AcWebServices / DesktopConnectorInterop

```
Python.Runtime.InternalPythonnetException: Failed to create Python type for AcWebServices
---> System.IO.FileNotFoundException: Could not load file or assembly 'DesktopConnectorInterop'
```

Caused by Revit loading `AcWebServices.dll` (references `DesktopConnectorInterop`, only present if Autodesk Desktop Connector is installed), triggered by `clr.AddReference` enumerating AppDomain assemblies. **Not our script.**

This error sometimes occurs only on the **first** `send_command` of a session and clears on the second attempt — **always retry once** before asking for a restart.

### Known: `module 'clr' has no attribute '_available_namespaces'`

Corrupted Python.NET state from startup — **not fixable at script level**. Only fix is restarting the host. Do not attempt workarounds (fake numpy injection, sys.meta_path manipulation). See [excel-mcp.md](excel-mcp.md), where this most often appears.
