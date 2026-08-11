<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform -->

<p align="center">
  <img src="https://raw.githubusercontent.com/RAEN-DT/PyNetLibrary/main/Assets/PyNetLibrary.png" width="400"/>
</p>

<p align="center">
  <a href="https://github.com/RAEN-DT/PyNetLibrary/releases"><img src="https://img.shields.io/github/v/release/RAEN-DT/PyNetLibrary?label=release&color=f78166" alt="Release"/></a>
  <img src="https://img.shields.io/badge/reference%20scripts-125%2B-2b7489" alt="Scripts"/>
  <img src="https://img.shields.io/badge/API%20stubs-189%20modules-6f42c1" alt="Stubs"/>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python"/>
  <img src="https://img.shields.io/badge/platform-Windows-lightgrey" alt="Windows"/>
  <img src="https://img.shields.io/badge/hosts-Navisworks%20%C2%B7%20Revit%20%C2%B7%20Civil%203D-orange" alt="Hosts"/>
</p>

#

**API context and reference scripts for Autodesk applications (Navisworks, Revit, Civil 3D)**, designed for the **[PyNet Platform](https://github.com/RAEN-DT/PyNet)**. This repo provides Python-style **stubs** of the Autodesk .NET APIs and example scripts, so that AI models (and developers) have the context they need to generate and understand automation code that runs through PyNet's embedded **Python.NET** engine.

> **AI Users:** This README, the API stubs under `02_PyNet Stubs/`, and the example scripts under `01_Scripts/` are the primary context sources for generating scripts. Read the execution environment and boilerplate sections before writing any code.

---

## ⚡ Quick Start

If you are an AI model or developer, you can quickly verify the environment with a minimal script:

**Navisworks:**
```python
import clr
clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import Application

doc = Application.ActiveDocument
print(doc.Title)
```

**Revit:**
```python
import clr
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

doc = __revit__.ActiveUIDocument.Document
print(doc.Title)
```

If either executes successfully inside PyNet, the environment is correctly configured.

---

## ⚙️ Execution Environment

Scripts run via **Python.NET** (CPython 3.10+ + `pythonnet` — not IronPython). This means standard Python 3 syntax is fully supported, along with the `clr` bridge to access .NET and Autodesk APIs.

| Property | Value |
| :--- | :--- |
| **CLR bridge** | `import clr` |
| **Standard Python** | ✅ Full Python 3.10+ |
| **pip packages** | ✅ Available |

**Key rules:**
- Always call `clr.AddReference(...)` before importing any Autodesk or System namespace.
- Use `List[T]` from `System.Collections.Generic` when passing collections to .NET methods.
- Navisworks UI dialogs use `System.Windows.Forms.MessageBox`. Revit scripts can use both WinForms and `Autodesk.Revit.UI.TaskDialog`.
- Revit write operations must be wrapped in a `Transaction`.

---

## 🧠 AI Usage Guidelines

When generating scripts for PyNet (Navisworks, Revit, Civil 3D), follow these rules:

### Structure
- Always use a class-based architecture
- Separate logic, UI, and orchestration
- Provide a single entry point (e.g. FeatureManager.Run(doc))

### Imports
- Always include required clr.AddReference(...) calls before importing .NET namespaces
- Only include imports that are required for the script to function

### API Usage
- **Navisworks:** use `Application.ActiveDocument` as the entry point to the model; prefer strongly typed API classes over dynamic access
- **Revit:** use `__revit__.ActiveUIDocument.Document`; wrap all write operations in a `Transaction`; use `FilteredElementCollector` for element queries
- When working with Clash or interface-heavy APIs in Navisworks, use `CastUtils.CastTo[T]` to avoid proxy objects

### UI interaction
- Use `System.Windows.Forms` for dialogs in both hosts
- In Revit, always import WinForms before `Autodesk.Revit.UI` to avoid `TaskDialog` name collision
- Never make Revit API calls inside WinForms event handlers — do all API work after `ShowDialog()` returns
- Avoid blocking UI threads unnecessarily

### Output
- Scripts should be self-contained and executable
- Avoid external dependencies unless explicitly allowed

### Safety
- Do not use restricted Python modules
- Do not attempt file system or system-level operations

### Deterministic Behavior
- Generate predictable and repeatable scripts
- Avoid ambiguous or dynamic runtime decisions
- Prefer explicit API calls over reflection or introspection

### Consistency
- Maintain consistent naming conventions across classes
- Follow the same structure across all generated scripts

---

## 📋 Standard Boilerplate

### Navisworks

```python
import clr
import sys
from pathlib import Path

clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import *

clr.AddReference("Autodesk.Navisworks.ComApi")
from Autodesk.Navisworks.Api.ComApi import *

clr.AddReference("Autodesk.Navisworks.Interop.ComApi")
from Autodesk.Navisworks.Api.Interop.ComApi import *

clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")

from System.Windows.Forms import *
from System.Drawing import *
from System.Collections.Generic import List

from Autodesk.Navisworks.Api import Application
doc = Application.ActiveDocument
```

For clash detection, add:
```python
clr.AddReference("Autodesk.Navisworks.Clash")
from Autodesk.Navisworks.Api.Clash import *
```

### Revit

```python
import clr
import System
from System import Enum, Environment
from pathlib import Path

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *

# __revit__ is injected by the PyNET plugin
doc = __revit__.ActiveUIDocument.Document
```

Any write operation requires a transaction:
```python
t = Transaction(doc, "Transaction name")
t.Start()
try:
    # write operations
    t.Commit()
except:
    t.RollBack()
    raise
```

For WinForms dialogs (import order is critical — WinForms before Revit UI):
```python
from Autodesk.Revit.DB import *
from System.Windows.Forms import *      # WinForms first
from System.Drawing import *
from Autodesk.Revit.UI import TaskDialog, TaskDialogCommonButtons, TaskDialogIcon
```

### AutoCAD / Civil 3D

Civil 3D runs on the AutoCAD platform and appears as **"AutoCAD"** in the active-instance list.

```python
import clr
from pathlib import Path

clr.AddReference("AcMgd")
clr.AddReference("AcCoreMgd")
clr.AddReference("AcDbMgd")
# Civil 3D only — add the AEC/Civil assemblies:
clr.AddReference("AecBaseMgd")
clr.AddReference("AeccDbMgd")

from Autodesk.AutoCAD.ApplicationServices import Application as AcadApp
from Autodesk.AutoCAD.DatabaseServices import *
from Autodesk.AutoCAD.EditorInput import Editor
from Autodesk.Civil.ApplicationServices import CivilApplication   # Civil 3D only
from Autodesk.Civil.DatabaseServices import *                     # Civil 3D only

doc = AcadApp.DocumentManager.MdiActiveDocument
db = doc.Database
ed = doc.Editor
civil_doc = CivilApplication.ActiveDocument                       # Civil 3D only
```

Write operations must be wrapped in a locked transaction:
```python
with doc.LockDocument():
    t = db.TransactionManager.StartTransaction()
    try:
        # write operations
        t.Commit()
    except:
        t.Abort()
        raise
```

## 🧪 Minimal Working Example

This example verifies that the Navisworks API and PyNet execution environment are correctly configured:

```python
import clr

clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import Application

from System.Windows.Forms import MessageBox

doc = Application.ActiveDocument

class FeatureManager:
    @staticmethod
    def Run(document):
        MessageBox.Show("Document loaded: " + document.Title)

FeatureManager.Run(doc)
```

---

## 🏗️ Code Structure Convention

All scripts follow a class-based pattern with a single entry-point call at the bottom:

```python
class FeatureManager:
    '''
    Main orchestrator class — coordinates the workflow
    by calling helper classes and presenting results to the user.
    Each public method represents a complete user action.
    '''
    @staticmethod
    def Run(document):
        data = DataProcessor.Process(document)
        DialogManager.ShowResult(data)

class DataProcessor:
    '''
    Business logic class — reads and transforms data from
    the Navisworks document. Returns plain Python objects
    that the rest of the script can consume.
    '''
    @staticmethod
    def Process(document):
        # business logic
        return result

class DialogManager:
    '''
    UI helper class — displays results or collects user input
    via System.Windows.Forms dialogs (MessageBox, OpenFileDialog, etc.).
    '''
    @staticmethod
    def ShowResult(data):
        MessageBox.Show(str(data), "PyNet", MessageBoxButtons.OK, MessageBoxIcon.Information)

# Entry point
FeatureManager.Run(doc)
```

---

## 🔍 Stub Usage

The stub files under `02_PyNet Stubs/Autodesk/` (one folder per host: `Navisworks/`, `Revit/`, `AutoCAD/`, `Civil/`, `Aec/`) provide a Python-style representation of the Autodesk .NET APIs.

### Purpose
- Provide type hints and method signatures
- Help AI models understand available API surfaces
- Improve code generation accuracy
- Assist developers in navigating the API

### How to Use
- Use stubs as a reference when writing scripts manually
- Use them as context for AI-generated code
- Explore them in an IDE for navigation and API understanding
- They are not required at runtime and should not be executed directly

### Notes
- Stubs mirror the structure of the Autodesk .NET assemblies
- They are purely informational and not executed at runtime

---

## 📂 Repository Structure

This repository contains two main types of resources:

- API stubs for Autodesk .NET APIs
- Example scripts demonstrating real-world usage patterns

### Navisworks — 01_Scripts/01_Navisworks/

Working scripts organized by use case:

- **Workflows** (`00_Workflows/`) — multi-step combined workflows (model update, coordination dashboard, coordination workflow).
- **Model Management** (`01_ModelManagement/`) — open, append, list and publish NWD files using the core Document API.
- **Search Sets** (`02_SearchSets/`) — create Search Sets from property conditions (`SearchCondition`, `VariantData`, `SearchLocations`).
- **Clash Detection** (`03_ClashDetection/`) — export, import, rename, run and auto-review clash tests; add comments; extract element info; generate clash images. Works with `doc.Clash.TestsData.Tests` via `CastUtils`.
- **Data Analysis** (`04_DataAnalysis/`, `08_DataAnalysis/`) — chart generation from clash data (bar charts, pie charts, stacked bars); interactive clash dashboard with IFC viewer integration.
- **Query Elements** (`05_QueryElements/`) — isolate and measure elements by property filters (foundations, panels, wall linear meters, unique parameter values); export clashes to JSON.
- **IFC Export** (`07_IFCExport/`) — geometry extraction and export to IFC/PNT format; includes a fast instanced-node exporter (`NavisworksPNT_IFC_Fast`) with per-category routing (FAST/INSTNODE/DIRECT).

### Revit — 01_Scripts/02_Revit/

Working scripts organized by use case:

- **Workflow** (`00_Workflow/`) — model sync, NWC export, parameter updates, key schedules, multi-model open/update, data transfer.
- **Selection — User Input** (`01_Selection User/`) — interactive element picking via `PickObject`, `PickObjects`, rectangle selection, and extending existing selections.
- **Selection — Filters** (`02_Selection Filter/`) — `FilteredElementCollector` patterns grouped by filter type:
  - *Quick filters* — `ElementCategoryFilter`, `ElementClassFilter`, `BoundingBoxIntersectsFilter`, `BoundingBoxInsideFilter`, `BoundingBoxContainsPointFilter`, `FamilySymbolFilter`, `ElementStructuralTypeFilter`, `IsCurveDrivenElementFilter`, `IsElementTypeFilter`, `ElementIdSetFilter`, `ElementDesignOptionFilter`, `ElementOwnerViewFilter`, `MultiCategoryFilter`, `MultiClassFilter`, `ExclusionFilter`
  - *Slow filters* — `ElementParameterFilter` (value-based filtering), `ElementIntersectsSolidFilter`
  - *Logical filters* — `LogicalAndFilter`, `LogicalOrFilter` (composing multiple filters)
  - *Special selections* — get element by Id, get doors/windows of a room, get panels of a room
- **Edit and Create Objects** (`03_Edit and Create Objects/`) — create walls, floors, holes, family instances, and transforms; move and rotate elements with `ElementTransformUtils`; edit wall profiles; undo rotations.
- **Units** (`04_Units/`) — convert between internal Revit units and display units using `UnitUtils`; comparison and conversion helpers.
- **Grids, Levels, Design Options, Phases** (`05_Grids Levels Design Options and Phases/`) — create grids and levels programmatically.
- **Task Dialogs** (`07_TaskDialog/`) — chained `TaskDialog` sequences with conditional branching.
- **Parameters** (`10_Parameters/`) — create shared parameters, project parameters, and PyNET-specific parameters; get categories bound to a parameter; transfer values between parameters; tag elements contained in a solid.
- **Families** (`13_Families/`) — inspect family parameters and their types at runtime.
- **Windows Forms** (`16_WindowsForms/`) — WinForms inside Revit: view filter forms, multi-model open/create/save workflow with full `Transaction` handling and `TaskDialog` confirmation.
- **Location and Coordinates** (`18_Location and Coordinates/`) — read and write `ProjectPosition` (origin, angle to true north).
- **Worksharing** (`20_Worksharing/`) — read Autodesk user login info from a workshared model.
- **Structure** (`23_Structure/`) — create structural beams, columns, wall foundations, and trusses using `NewFamilyInstance` and `NewBeam`.
- **MEP** (`24_MEP/`) — create ducts (`Duct.Create`) and electrical wires (`Wire.Create`) with connectors and curve endpoints.
- **QA/QC** (`25_QAQC/`) — model audit against BEP standards with HTML + Excel scored report (`ModelAudit.py`); type renaming to fix nomenclature.
- **5D** (`26_5D/`) — quantity takeoff / budget extraction: matches model quantities to a reference Excel and generates a measurement breakdown + interactive HTML report (`QuantityTakeoff.py`).

### AutoCAD / Civil 3D — 01_Scripts/03_AutoCAD/

Civil 3D runs on the AutoCAD platform and appears as **"AutoCAD"** in the active-instance list. Working scripts organized by use case:

- **Layers** (`01_Layers/`) — list and manage layers.
- **Blocks** (`02_Blocks/`) — list block definitions; insert blocks.
- **Entities** (`03_Entities/`) — list model-space entities; read, create and use property sets; zoom to objects by property set.
- **Windows Forms** (`04_WinForms/`) — WinForms in AutoCAD: create DWG files from a dialog; edit existing DWGs (background and UI patterns).
- **Layouts** (`05_Layouts/`) — list layouts.
- **Alignments** (`10_Alignments/`) — list Civil 3D alignments.
- **Profiles** (`11_Profiles/`) — list profiles.
- **Surfaces** (`12_Surfaces/`) — list surfaces and surface statistics.
- **Corridors** (`13_Corridors/`) — list corridors.
- **Pipe Networks** (`15_Pipe_Networks/`) — list pipe networks.

Example — `SearchSetsManager.CreateSet` from 02_SearchSets/GenerateSearchSets.py:

```python
import clr

clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import *

clr.AddReference("Autodesk.Navisworks.ComApi")
from Autodesk.Navisworks.Api.ComApi import *

clr.AddReference("Autodesk.Navisworks.Interop.ComApi")
from Autodesk.Navisworks.Api.Interop.ComApi import *

clr.AddReference("Autodesk.Navisworks.Clash")
from Autodesk.Navisworks.Api.Clash import *

from System.Collections.Generic import List

from Autodesk.Navisworks.Api import Application 
doc = Application.ActiveDocument

class SearchSetsManager():
    @staticmethod
    def CreateSet(value, selectionSets):
        '''
        Creates a new Search Set filtered by a property value.
        Searches "Clash Test Code" under both "Revit Type" and "Element"
        categories (OR logic via separate groups), then registers the
        resulting set in the document's SelectionSets collection.
        '''
        searchSet = Search()
        searchSet.Locations = SearchLocations.DescendantsAndSelf
        searchSet.Selection.SelectAll()

        # First condition group — match by "Revit Type" category
        condition = SearchCondition.HasPropertyByDisplayName("Revit Type", "Clash Test Code")
        conditionValue = condition.EqualValue(VariantData.FromDisplayString(value))
        searchSet.SearchConditions.AddGroup(List[SearchCondition]([conditionValue]))

        # Second condition group (OR) — match by "Element" category
        conditionOr = SearchCondition.HasPropertyByDisplayName("Element", "Clash Test Code")
        conditionValueOr = conditionOr.EqualValue(VariantData.FromDisplayString(value))
        searchSet.SearchConditions.AddGroup(List[SearchCondition]([conditionValueOr]))

        # Create the SelectionSet and add it to the document
        instance = SelectionSet(searchSet)
        instance.DisplayName = value
        selectionSets.AddCopy(instance)
```

---

## 🗒️ Common Patterns

Below are frequently used patterns when working with the Navisworks API:

```python
### Access Active Document

doc = Application.ActiveDocument

### Iterate Model Items

for item in doc.Models[0].RootItem.DescendantsAndSelf:
    print(item.DisplayName)

### Access Properties

props = item.PropertyCategories

### Working with Selection Sets

selection_sets = doc.SelectionSets

### Run a Search

search = Search()
search.Selection.SelectAll()
```

---

## ❓ FAQs

Have questions about installation, configuration, or usage? Check the full FAQ page:

👉 [PyNet FAQs](https://github.com/RAEN-DT/PyNet/wiki/PyNET-FAQs)

---

## 🔗 How This Library Fits Into the Ecosystem

This library is part of a modular system designed to enable AI-driven BIM automation across Autodesk tools.

This repository is designed to work alongside:

- PyNet Platform → Executes scripts inside Navisworks via Python.NET  
- PyNet Bridge (MCP) → Connects AI models to PyNet locally  

Together, these components enable:

Natural Language → AI → Python Script → PyNet → Navisworks / Revit / Civil 3D → BIM Action

| Component | Repository | Purpose |
| :--- | :--- | :--- |
| **PyNet Platform** | [PyNet](https://github.com/RAEN-DT/PyNet) | Navisworks/Revit plugin — hosts the Python.NET engine |
| **PyNet Bridge (MCP)** | [PyNetBridge](https://github.com/RAEN-DT/PyNetBridge) | MCP server - connects AI models to PyNET with including secure scripts validation|
| **PyNet Library** | This repo | Script reference library and AI context |

To have AI generate and execute scripts live against Navisworks or Revit, install the MCP server:

```powershell
irm https://raw.githubusercontent.com/RAEN-DT/PyNetBridge/main/install.ps1 | iex
```

This auto-detects and configures **Claude Desktop**, **Claude Code**, **Cline**, and **Roo Code**.

---

## 🖥️ BIM Viewer & Coordination Dashboard

The viewer is an embeddable web component built with **ThatOpen Components** for visualizing
federated IFC models alongside coordination data (clash detection) exported from Navisworks.

> **The viewer source now lives in [PyNetVSCode](https://github.com/RAEN-DT/PyNetVSCode)**, under
> `viewer/`, together with the VS Code extension that ships it. Build instructions, the development
> server and the viewer's public JavaScript API are documented there. This repo keeps the parts that
> belong to the Autodesk side: producing the `.pnt` package and launching the dashboard from
> Navisworks.

### The `.pnt` package

A `.pnt` file is the portable coordination package: a **ZIP bundle** containing the federated
IFC models (`models/*.ifc`) plus the clash data (`clashes.json`). It makes a whole coordination
snapshot a single self-contained file that opens in the dashboard without any loose files.

### Launch from Navisworks (recommended)

The dashboard is launched directly from Navisworks via a Ribbon button:

**Tab "Dashboard"** → Button **"Export Clashes"**

This opens a WinForms dialog with two actions:
1. **Export Clashes** — runs all clash tests and exports `clashes.json` to the IFC directory of the active model
2. **Launch Dashboard** — starts the web server in a thread, automatically kills any previous server on the same port, and opens the browser

The script is located at `01_Scripts/01_Navisworks/04_DataAnalysis/ExportClashDashboard.py`.

> **Important limitation:** The web server (Dash/Flask) only works when launched from a **WinForms** context (`Form.ShowDialog()`). Launching Dash from a direct MCP script (`send_command`) causes a deadlock due to the Python.NET GIL. This is why the script uses a Form as its entry point — the server thread is created from the Form button event, not from the MCP context.

### Opening a `.pnt` package

The easiest route is the **PyNET extension for VS Code**, which bundles the viewer and opens a
`.pnt` in an editor tab. To run the server directly, or to build the viewer from source, see the
[PyNetVSCode](https://github.com/RAEN-DT/PyNetVSCode) repo — `viewer/README.md` covers
`pnt_server.py`, the standalone `.exe`, the hot-reload dev server and the viewer's public API.

For how the `.pnt` is produced from a model, see [docs/pnt-export.md](docs/pnt-export.md). For
driving an already-loaded package from the AI side, see [docs/viewer-mcp.md](docs/viewer-mcp.md).

---

## ⚠️ Notes and Limitations

### Runtime Limitations
- Scripts run inside the Autodesk application context (Navisworks, Revit, Civil 3D)
- File system and OS-level operations are restricted
- Certain Python standard libraries are not available due to security constraints

### Compatibility
- Requires Autodesk applications with Python.NET support via PyNet Platform
- Compatible with Python 3.10+
- **Python 3.14 is supported.**
- Behavior may vary depending on application version
- API access depends on Autodesk application version and edition compatibility

---

<p align="center">
  <img src="https://raw.githubusercontent.com/RAEN-DT/PyNetLibrary/main/Assets/RAENDigitalTools.png" alt="RAEN Digital Tools" width="180"><br/><br/>
  <sub>© 2026 RAEN Digital Tools · Todos los derechos reservados.<br/>
  Obra inscrita en el Registro de la Propiedad Intelectual de la Comunidad de Madrid.</sub>
</p>
