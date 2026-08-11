<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform -->

# Guide: API stubs & IntelliSense

Read this guide when **generating stubs** or **setting up VS Code IntelliSense**.

Stubs live in `02_PyNet Stubs/` (committed). Pylance resolves them via `python.analysis.extraPaths`.

---

## Structure

```
02_PyNet Stubs/
  _index/
    CLASSES.tsv   <- the lookup index; read this before touching a stub file
    STATS.md      <- corpus summary, classes per namespace
  Autodesk/
    Navisworks/   <- generated from the open Navisworks version
    Revit/        <- generated from the open Revit version
    Aec/ AutoCAD/ Civil/   <- AutoCAD / Civil 3D
  System/         <- only what PyNET imports: Windows.Forms, Drawing, Collections
```

`System/` is deliberately narrow. WPF (`System.Windows.Controls`, `.Media`) and the rest of the
BCL were removed — the library imports WinForms, Drawing and Collections.Generic and nothing else,
and carrying 17 MB of stubs nobody consults made every search slower. The stub files contain no
imports, so a missing subtree cannot break another one; Pylance simply offers no completion for it.

---

## Looking up a class — do this, not a blind grep

A single namespace file can be 25k lines, so never `Read` one whole and never grep the corpus to
find *where* something is. `_index/CLASSES.tsv` (942 KB, 8,788 classes) makes them addressable:

```
class      namespace             file                            start   end   base        members
Wall       Autodesk.Revit.DB     Autodesk/Revit/DB/__init__.py   25358   25421 HostObject  58
```

**Two steps, both cheap:**

1. `Grep` the index for the class name → gives the namespace (so you know the import line), the
   file, and the exact line range.
2. `Read` that file with `offset=start`, `limit=end-start` → you get the class and nothing else.
   The median class is 16 lines; the 90th percentile is 142.

**163 class names exist in more than one namespace** (`Application` is in six, `Entity` in five).
Always match on the `namespace` column — never assume the first hit is the right one.

To find *which* class has a given method or property, grep the stub files directly: ripgrep reports
the file and line, and that is cheaper than a second index would be. The index carries only what
grep cannot produce — the line range and the disambiguating namespace.

### Rebuilding the index

```powershell
python 01_Scripts\00_utils\IndexStubs.py
```

Runs with local CPython — no host, no bridge. **Re-run it after every `GenerateStubs.py`**, since
the line numbers are only valid for the stubs they were built from.

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
