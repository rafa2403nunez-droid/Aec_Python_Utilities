<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform -->

# Guide: API stubs & IntelliSense

Read this guide when **generating stubs** or **setting up VS Code IntelliSense**.

Stubs live in `02_PyNet Stubs/` (committed). Pylance resolves them via `python.analysis.extraPaths`.

---

## Structure

```
02_PyNet Stubs/
  Autodesk/
    Navisworks/   <- generated from the open Navisworks version
    Revit/        <- generated from the open Revit version
    Aec/ AutoCAD/ Civil/   <- AutoCAD / Civil 3D
  System/         <- legacy .NET stubs (kept for intellisense)
```

> These files are very large (50k+ lines). **Never read them in full.** Search for a specific class/method/property only when other context sources don't answer.

---

## IntelliSense setup (VS Code)

For Pylance to resolve `Wall`, `FilteredElementCollector`, `Search`, etc., the stubs path must be in user settings.

**Check on session start:** does `python.analysis.extraPaths` include the stubs folder?

```
%APPDATA%\Pynet\Library\02_PyNet Stubs
```

Settings file: `C:\Users\<user>\AppData\Roaming\Code\User\settings.json`

If missing, ask the user whether they write scripts and want autocomplete:

> "I can configure VS Code so it suggests Revit/Navisworks API classes and methods as you type — like autocomplete for the API. One-time setup. Want me to set it up?"

Then add the path. Create `settings.json` if absent; never modify other existing settings.

---

## Generating stubs

Run `01_Scripts/00_utils/GenerateStubs.py` from the active host via `send_command`. It:

1. Auto-detects the host (Revit `__revit__` global present, else Navisworks/AutoCAD).
2. Loads the relevant assemblies for that host.
3. Deletes only `Autodesk/<Host>/` — hosts coexist.
4. Regenerates with valid Python syntax.
5. Writes directly to `02_PyNet Stubs/`.

**One set of stubs per host, always the currently open version.** Don't keep stubs for multiple versions of the same host — Pylance would see conflicting definitions.

### Assembly sets

| Host | Assemblies |
|------|-----------|
| Navisworks | `Autodesk.Navisworks.Api`, `.ComApi`, `.Interop.ComApi`, `.Clash` |
| Revit | `RevitAPI`, `RevitAPIUI` |
| Civil 3D | `AcMgd`, `AcCoreMgd`, `AcDbMgd`, `AecBaseMgd`, `AeccDbMgd` |

### Type mappings

| .NET | Python stub |
|------|-------------|
| `String` | `str` |
| `Boolean` | `bool` |
| `Int32` / `Int64` | `int` |
| `Double` / `Single` | `float` |
| `Void` | `None` |
| `T[]` (array) | `list` |
| `T&` (by-ref / out) | same as `T` |
| `T*` (pointer) | same as `T` |
| Python keyword param names | append `_` (e.g. `type_`, `from_`, `in_`) |
