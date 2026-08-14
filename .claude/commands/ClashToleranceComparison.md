# Skill: ClashToleranceComparison

Full workflow for comparing clash results across different tolerance scenarios in Navisworks via PyNET.
Runs the tests on the live model, copies the file, applies new tolerances, runs again and produces a
side-by-side Excel comparison.

> **Related skill:** [ClashDetection.md](ClashDetection.md) — context on SearchSets, approval criteria
> and the full clash matrix setup that feeds into this workflow.

---

## Context

- Navisworks API uses **feet** internally → always convert: `mm / 1000 / 0.3048`
- `ClashTest` objects are **read-only by ownership**. Direct assignment (`test.Tolerance = x`)
  raises `System.NotSupportedException: Object is Read-Only`.
  The only supported edit paths are:
  - **Via copy** — `CreateCopy()` + `TestsEditTestFromCopy()` (modifies in-place)
  - **Via duplicate** — `DuplicateTest()` creates an independent sibling test
- NWF files are **binary** (LcUStream format) — cannot be edited as XML. Copy with
  `pathlib` bytes read/write; modify tolerances via the API after opening.
- Correct path to tests: `testsData.Value.TestsRoot.Children` — never `testsData.Tests`.
- `DocumentClash` requires `CastUtils.CastTo[DocumentClash](doc.Clash)` — direct cast fails.

---

## Workflow

### 0. Verify session

```python
# Always call list_active_instances first.
# Civil 3D appears as "AutoCAD". This workflow targets Navisworks only.
```

### 1. Run baseline tests and export to Excel

Run all clash tests on the currently open model and export raw results to Excel.

```python
import clr
import sys
from pathlib import Path

clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import Application

clr.AddReference("Autodesk.Navisworks.Clash")
from Autodesk.Navisworks.Api.Clash import DocumentClash, ClashResultStatus

# ── CastUtils (required for DocumentClash) ────────────────────────────────────
bundle_base = (
    Path.home() / "AppData" / "Roaming" / "Autodesk" / "ApplicationPlugins"
    / "RAEN.Navisworks.PyNET.bundle" / "Contents"
)
# Resolve the actual year folder (2024 / 2025 / 2026 / 2027)
bundle_path = next(
    (d for d in bundle_base.iterdir()
     if d.is_dir() and (d / "Raen.Core.Pynet.Resources.dll").exists()),
    None,
)
if bundle_path is None:
    raise RuntimeError("PyNET bundle not found.")
sys.path.append(str(bundle_path))
clr.AddReference("Raen.Core.Pynet.Resources")
from Raen.Core.Pynet.Resources import CastUtils  # type: ignore

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

doc = Application.ActiveDocument
clash_doc = CastUtils.CastTo[DocumentClash](doc.Clash)
tests_data = clash_doc.TestsData

# ── Run all tests ──────────────────────────────────────────────────────────────
tests_data.TestsRunAllTests()

# ── Status display map ─────────────────────────────────────────────────────────
STATUS_MAP = {
    str(ClashResultStatus.New): "New",
    str(ClashResultStatus.Active): "Active",
    str(ClashResultStatus.Reviewed): "Reviewed",
    str(ClashResultStatus.Approved): "Approved",
    str(ClashResultStatus.Resolved): "Resolved",
}

def export_results_to_excel(tests_data, out_path: Path, sheet_title: str, header_color: str):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_title
    headers = ["Test", "Tolerance (mm)", "Clash Name", "Status", "Distance (mm)"]
    ws.append(headers)
    for cell in ws[1]:
        cell.fill = PatternFill("solid", fgColor=header_color)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="center")
    summary = []
    for test in tests_data.Value.TestsRoot.Children:
        tol_mm = round(test.Tolerance * 0.3048 * 1000, 2)
        clashes = list(test.Children)
        summary.append({"test": test.DisplayName, "tolerance_mm": tol_mm, "total": len(clashes)})
        for clash in clashes:
            status_str = STATUS_MAP.get(str(clash.Status), str(clash.Status))
            dist_mm = round(clash.Distance * 0.3048 * 1000, 2) if hasattr(clash, "Distance") else ""
            ws.append([test.DisplayName, tol_mm, clash.DisplayName, status_str, dist_mm])
    wb.save(str(out_path))
    return summary

model_dir = Path(doc.FileName).parent
baseline_excel = model_dir / "Clashes_Baseline.xlsx"
baseline_summary = export_results_to_excel(tests_data, baseline_excel, "Baseline", "1F4E79")
ia_Result = {"excel": str(baseline_excel), "tests": baseline_summary}
```

### 2. Copy the model file

NWF/NWD files are binary — copy with `pathlib` bytes:

```python
src = Path(doc.FileName)
dst = src.parent / f"{src.stem}_15mm{src.suffix}"
dst.write_bytes(src.read_bytes())
# ia_Result = {"copied_to": str(dst)}
```

### 3. Open the copy in Navisworks

```python
doc.OpenFile(str(dst))
# After this call doc.FileName == dst
# The baseline Excel is already saved — no data is lost when the file switches.
```

### 4. Change tolerances — two approaches

#### Approach A — edit tests in place (via copy)

`ClashTest` is read-only; `set_Tolerance()` can only be called on a detached copy.
`TestsEditTestFromCopy` applies the mutation back to the live test atomically.

```python
TOLERANCE_MM = 15.0
TOLERANCE_FT = TOLERANCE_MM / 1000 / 0.3048

# Optional filter — leave empty to apply to ALL tests
TARGET_TESTS: list[str] = []

clash_doc = CastUtils.CastTo[DocumentClash](doc.Clash)
tests_data = clash_doc.TestsData

for test in tests_data.Value.TestsRoot.Children:
    if TARGET_TESTS and test.DisplayName not in TARGET_TESTS:
        continue
    copy = test.CreateCopy()
    copy.set_Tolerance(TOLERANCE_FT)
    tests_data.TestsEditTestFromCopy(test, copy)
```

> **Why `CreateCopy` and not direct assignment?**
> `ClashTest.Tolerance` has a `set_Tolerance` setter but the API enforces an ownership lock at
> runtime (`NativeHandle.RuntimeChecks`). Direct assignment raises `NotSupportedException`.
> `TestsEditTestFromCopy` is the official mutation gate — it temporarily lifts the lock,
> applies all changed fields from the copy, and re-locks.

#### Approach B — duplicate test, set different tolerance on the copy

Keeps the original test intact alongside a new variant. Useful for side-by-side in-document
comparisons without overwriting the source configuration.

```python
def duplicate_test_with_tolerance(tests_data, source_name: str, new_name: str, tolerance_mm: float):
    tolerance_ft = tolerance_mm / 1000 / 0.3048
    source = next(
        (t for t in tests_data.Value.TestsRoot.Children if t.DisplayName == source_name),
        None,
    )
    if source is None:
        return {"error": f"Test not found: {source_name}"}

    duplicate = source.DuplicateTest()
    tests_data.TestsEditDisplayName(duplicate, new_name)

    copy = duplicate.CreateCopy()
    copy.set_Tolerance(tolerance_ft)
    tests_data.TestsEditTestFromCopy(duplicate, copy)

    return {"source": source_name, "duplicate": new_name, "tolerance_mm": tolerance_mm}

# Example — duplicate every test with a "_15mm" suffix
results_b = []
# Snapshot the list first — iterating while DuplicateTest adds siblings is unsafe
original_tests = list(tests_data.Value.TestsRoot.Children)
for test in original_tests:
    r = duplicate_test_with_tolerance(tests_data, test.DisplayName, f"{test.DisplayName}_15mm", 15.0)
    results_b.append(r)
```

| | Approach A | Approach B |
|---|---|---|
| Original test | **overwritten** | **kept** |
| Result history | cleared on next run | independent per test |
| Use when | comparing scenarios across files | side-by-side within same file |

### 5. Run tests on the copy and export

```python
tests_data.TestsRunAllTests()

new_excel = model_dir / "Clashes_15mm.xlsx"
new_summary = export_results_to_excel(tests_data, new_excel, "15mm", "375623")
ia_Result = {"excel": str(new_excel), "tests": new_summary}
```

### 6. Build comparison Excel

```python
from openpyxl.styles import Border, Side

def build_comparison(baseline: list[dict], scenario: list[dict], out_path: Path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Comparacion"

    hdr_blue  = PatternFill("solid", fgColor="1F4E79")
    hdr_green = PatternFill("solid", fgColor="375623")
    hdr_dark  = PatternFill("solid", fgColor="2E2E2E")
    gained    = PatternFill("solid", fgColor="FFC000")   # more clashes
    lost      = PatternFill("solid", fgColor="70AD47")   # fewer clashes
    neutral   = PatternFill("solid", fgColor="D9D9D9")
    center    = Alignment(horizontal="center")
    bold_wht  = Font(bold=True, color="FFFFFF")
    bold      = Font(bold=True)

    # Merged header row
    ws.merge_cells("A1:A2"); ws["A1"] = "Test"
    ws.merge_cells("B1:C1"); ws["B1"] = "Baseline"
    ws.merge_cells("D1:E1"); ws["D1"] = f"{scenario[0]['tolerance_mm']} mm"
    ws.merge_cells("F1:F2"); ws["F1"] = "Δ Clashes"
    for coord, fill in [("A1", hdr_dark), ("B1", hdr_blue), ("D1", hdr_green), ("F1", hdr_dark)]:
        ws[coord].fill = fill; ws[coord].font = bold_wht; ws[coord].alignment = center

    ws["B2"] = "Tolerance (mm)"; ws["C2"] = "Clashes"
    ws["D2"] = "Tolerance (mm)"; ws["E2"] = "Clashes"
    for col in ["B2", "C2", "D2", "E2"]:
        ws[col].font = bold; ws[col].alignment = center

    ws.column_dimensions["A"].width = 20
    for col in ["B", "C", "D", "E", "F"]:
        ws.column_dimensions[col].width = 18

    idx_map = {r["test"]: r for r in scenario}
    total_b = total_n = 0
    for row_i, b in enumerate(baseline, start=3):
        n = idx_map.get(b["test"], {"tolerance_mm": "-", "total": 0})
        delta = n["total"] - b["total"]
        total_b += b["total"]; total_n += n["total"]
        ws.cell(row_i, 1, b["test"])
        ws.cell(row_i, 2, b["tolerance_mm"]).alignment = center
        ws.cell(row_i, 3, b["total"]).alignment = center
        ws.cell(row_i, 4, n["tolerance_mm"]).alignment = center
        ws.cell(row_i, 5, n["total"]).alignment = center
        d = ws.cell(row_i, 6, f"+{delta}" if delta > 0 else str(delta))
        d.alignment = center
        d.fill = gained if delta > 0 else (lost if delta < 0 else neutral)
        if delta != 0: d.font = bold

    last = 3 + len(baseline)
    ws.cell(last, 1, "TOTAL").font = bold
    ws.cell(last, 3, total_b).font = bold; ws.cell(last, 3).alignment = center
    ws.cell(last, 5, total_n).font = bold; ws.cell(last, 5).alignment = center
    delta_t = total_n - total_b
    d_total = ws.cell(last, 6, f"+{delta_t}" if delta_t > 0 else str(delta_t))
    d_total.font = bold; d_total.alignment = center
    d_total.fill = gained if delta_t > 0 else (lost if delta_t < 0 else neutral)

    wb.save(str(out_path))
    return {"excel": str(out_path), "total_baseline": total_b, "total_new": total_n, "delta": delta_t}

comparison_excel = model_dir / "Clashes_Comparacion.xlsx"
result = build_comparison(baseline_summary, new_summary, comparison_excel)
ia_Result = result
```

---

## Output files

| File | Contents |
|------|----------|
| `Clashes_Baseline.xlsx` | Raw results with original tolerances, one row per clash |
| `Clashes_15mm.xlsx` | Raw results after new tolerance, same format |
| `Clashes_Comparacion.xlsx` | Side-by-side table: test · baseline tol/count · new tol/count · Δ |
| `<ModelName>_15mm.nwf` | Copy of the original model with modified tolerances |

Color coding in the comparison sheet:
- **Orange** — more clashes with new tolerance (newly detected interferences)
- **Green** — fewer clashes (some resolved or no longer triggered)
- **Grey** — no change

---

## Adaptation checklist

When running this workflow on a new project:

1. **`TOLERANCE_MM`** — set the target tolerance value (default `15.0`).
2. **`TARGET_TESTS`** — list specific test names to limit scope, or leave `[]` for all.
3. **`bundle_path` resolution** — the auto-detect loop (`Raen.Core.Pynet.Resources.dll`) handles
   all bundle year folders. No manual change needed unless the bundle location is non-standard.
4. **Output folder** — `model_dir = Path(doc.FileName).parent` places all files next to the model.
   Change to any writable path if needed.
5. **Approach A vs B** — A overwrites tolerances in-place (best for scenario files); B duplicates
   tests inside the same document (best for quick side-by-side without a second file).
6. **Excel header colors** — `"1F4E79"` (blue) for baseline, `"375623"` (green) for scenario.
   Pass any 6-char hex string to `export_results_to_excel`.

---

## Common pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| `NotSupportedException: Object is Read-Only` | Assigning `test.Tolerance = x` directly | Use `CreateCopy()` + `set_Tolerance()` + `TestsEditTestFromCopy()` |
| `AttributeError: 'Document' object has no attribute 'GetClash'` | Using `doc.GetClash()` (COM pattern) | Use `CastUtils.CastTo[DocumentClash](doc.Clash)` |
| `name 'Autodesk' is not defined` | Missing explicit `AddReference` before import | Add `clr.AddReference("Autodesk.Navisworks.Clash")` before `from Autodesk.Navisworks.Api.Clash import …` |
| `TestsEditTestFromCopy` applies nothing | Copy mutated after passing to the method | Mutate the copy **before** passing it; the method reads all fields at call time |
| Iterating while duplicating adds siblings mid-loop | `DuplicateTest` appends to `TestsRoot.Children` | Snapshot the list first: `original_tests = list(tests_data.Value.TestsRoot.Children)` |
| NWF XML edit produces unreadable file | NWF is LcUStream binary, not XML | Use `pathlib` bytes copy + API tolerance edit after `OpenFile` |

---

<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform -->
