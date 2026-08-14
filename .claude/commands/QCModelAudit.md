# Skill: QCModelAudit

Start the conversation in english. If the user request to change you can use the user language.

Quality Control audit workflow for Revit models on the PyNET platform. Reads a configuration Excel, checks the model against BEP standards, and generates an HTML + Excel report with score and grade.

> **Read first:** [RevitApiPatterns.md](RevitApiPatterns.md) — all element/type querying patterns used here (collector queries, ElementId, area BIPs) follow those rules.

## Context

- **Host:** Revit only (uses `__revit__` global)
- **Config Excel:** defined by the user — path hardcoded in `EXCEL_PATH`. Contains all rules.
- **Output:** timestamped HTML and Excel in the same folder as the config Excel.
- **Guard required:** always include the `_available_namespaces` guard before `import openpyxl` (or rely on plugin v1.4.8+ which sets the guard in C# before any script executes).
- **Coordinate units:** Excel stores E/O, N/S, Elevation in **tenths of mm** (0.1 mm). Divide by 10 before comparing with Revit values (in mm via `ft * 304.8`).

---

## Excel structure

| Sheet | Content |
|---|---|
| `Fichero` | Key-value config: `Tamanio_Max_MB`, `Version_Min_Revit` |
| `Modelo` | Key-value: `Max_Advertencias`, `Parametros_Compartidos` |
| `Coordenadas` | Key-value: `Tolerancia_PBP_Survey_mm`, `E/O`, `N/S`, `Elevacion` (tenths of mm), `Angulo Norte real` (degrees), `Links_Por_Coordenadas` |
| `Disciplinas` | Group → discipline code (e.g. ARQ, EST, MEP) |
| `Clasificaciones` | BIC_STR, …, category_name, code pairs |
| `Matriz` | BIC_STR, group, category, then param columns with `T` (type) or `E` (instance) |
| `Planos` | Required sheet parameters and expected values |
| `Proyecto` | Required ProjectInformation parameters and expected values |

---

## Sections checked

| Section | What it checks |
|---|---|
| **Fichero** | File name format, size, Revit version |
| **Modelo** | Worksharing, worksets, warnings count, shared parameters file, unused families |
| **Coordenadas** | PBP shared coords vs Excel BEP values; PBP position vs internal origin (0,0,0); link anchoring |
| **Proyecto** | ProjectInformation parameters vs BEP expected values |
| **Planos** | Sheet number format (DISC-NNN), required sheet parameters |
| **Parametros** | Type and instance parameters from matrix — missing or empty |
| **Nomenclatura Tipos** | Type names follow `DISC_Category_Code_Description` pattern |
| **Nomenclatura Familias** | Family names follow same pattern (loadable families only) |

---

## Scoring

Weighted average of per-section OK rate × 10:

| Section | Weight |
|---|:---:|
| Fichero | 1 |
| Modelo | 2 |
| Coordenadas | 2 |
| Proyecto | 1 |
| Planos | 2 |
| Parametros | 3 |
| Nomenclatura Tipos | 2 |
| Nomenclatura Familias | 2 |

Grade: A ≥ 9 · B ≥ 7 · C ≥ 5 · D ≥ 3 · F < 3

---

## Workflow

### 1. Check active instance
```python
list_active_instances  # must be Revit
```

### 2. Ask the user for the Excel path
If not provided, check `AI_History` for a recent run and reuse the path. The Excel path is also the output directory for reports.

### 3. **VALIDATE Excel format before executing** ⚠️

**Do NOT skip this step.** Open the Excel file and verify:
- All 8 required sheets exist: `Fichero`, `Modelo`, `Coordenadas`, `Disciplinas`, `Clasificaciones`, `Matriz`, `Planos`, `Proyecto`
- Each sheet contains at least the key columns listed above (see "Validate Excel format" section)
- No missing rows or malformed structure

If the Excel is incomplete or corrupt, the audit will fail or produce meaningless results. Ask the user to fix the Excel before proceeding.

### 4. Execute the script via `send_command_by_path`

Use the production script directly by path. Update only the `EXCEL_PATH` variable inside the file if needed.

```python
send_command_by_path(
    pid=<pid>,
    script_name="QC_ModelAudit",
    file_path=r"C:\Users\34655\source\repos\GithubRNM\PyNetLibrary\01_Scripts\02_Revit\25_QAQC\ModelAudit.py",
    timeout=120
)
```

Timeout: **≥ 120 seconds** — the script iterates all elements of all categories in the model.

### 5. Report results

Present the score/grade and key findings from the HTML report.

### 6. If the user wants to iterate

Re-run with the same script after the user adjusts the model or Excel config. The script is self-contained — no state persists between runs.

---

## Key implementation notes

### Coordinate comparison
```python
# Excel stores coords in tenths of mm — divide by 10 to get mm
exp_mm = float(excel_val) / 10.0
diff = abs(revit_val_mm - exp_mm)
```

### ElementId compatibility (Revit 2024+)
```python
def eid_val(eid):
    try: return int(eid.Value)        # Revit 2024+
    except: return int(eid.IntegerValue)  # older versions
```

### No `import System`
When using the `_available_namespaces` guard, do not import `System`. Substitutions:
- `Environment.GetFolderPath` → use the Excel folder as output dir
- `Enum.Parse(BuiltInCategory, ...)` → use a `BIC_MAP` dict literal

### grouped_tbl — Check column
In Parametros / Nomenclatura sections, the table shows a **Parametro** column extracted from `r['Check'].split('/')[-1]`. The full Check field format is `CategoryName/ParameterName` and `CategoryName/Resumen`.

---

## Production script

- **Location:** `01_Scripts\02_Revit\25_QAQC\ModelAudit.py`
- **This is the single source of truth** — all improvements go on this file. No versioned copies.
- **Always execute via `send_command_by_path`** pointing to this path — never copy the content inline.
- Only change before running: update `EXCEL_PATH` inside the file to point to the correct QC config Excel for the project.
- The script auto-derives `OUTPUT_DIR` from the Excel path.

### Before running: Validate Excel format

**CRITICAL:** Before executing, verify the config Excel has the correct structure:

| Sheet | Required | Columns |
|---|---|---|
| `Fichero` | ✓ | `Tamanio_Max_MB`, `Version_Min_Revit` |
| `Modelo` | ✓ | `Max_Advertencias`, `Parametros_Compartidos` |
| `Coordenadas` | ✓ | `Tolerancia_PBP_Survey_mm`, `E/O`, `N/S`, `Elevacion` (tenths mm), `Angulo Norte real` |
| `Disciplinas` | ✓ | Group code → discipline code (ARQ, EST, MEP, etc.) |
| `Clasificaciones` | ✓ | BIC_STR, Group, category_name, classification_code pairs |
| `Matriz` | ✓ | BIC_STR, Group, Category, then param columns flagged `T` (type) or `E` (instance) |
| `Planos` | ✓ | Sheet param names, obligation flag (True/False), expected values |
| `Proyecto` | ✓ | ProjectInformation param names, obligation flag, expected values |

**If any sheet is missing or malformed, the script will fail or produce incomplete results.**

### BIC_MAP (36 categories — do not modify)
```python
BIC_MAP = {
    'OST_Walls': BuiltInCategory.OST_Walls,
    'OST_Floors': BuiltInCategory.OST_Floors,
    # ... (full map in the executed script)
}
```

### HTML output
Self-contained single-file HTML with:
- Sticky header with model name and score
- Sidebar navigation with color-coded sections
- KPI row (total, errors, warnings, OK)
- Donut chart (SVG, inline)
- Per-section bar chart
- Section cards (click to scroll)
- Collapsible grouped tables for Parametros / Nomenclatura sections — each group shows a **Parametro** column

### Excel output
One sheet per section, columns: `Check | Estado | Detalle | ElementId`. Color-coded rows (green/red/yellow).

---

## Iterating on the script

All improvements go directly on `ModelAudit.py`. Workflow:

1. Edit the file with the improvement
2. Re-run via `send_command_by_path` to validate
3. Repeat — no versioned copies, no inline content

---

## Excel validation checklist

Before launching QC audit, use this checklist to verify the config Excel:

- [ ] File exists and is readable
- [ ] Sheet `Fichero` exists with `Tamanio_Max_MB` and `Version_Min_Revit` 
- [ ] Sheet `Modelo` exists with `Max_Advertencias` and `Parametros_Compartidos`
- [ ] Sheet `Coordenadas` exists with tolerance and BEP coords (in tenths of mm)
- [ ] Sheet `Disciplinas` exists with Group codes (ARQ, EST, MEP, GEN, etc.)
- [ ] Sheet `Clasificaciones` exists with BIC_STR, Group, category_name, code pairs
- [ ] Sheet `Matriz` exists with BIC_STR, Group, Category, and param columns (T/E flags)
- [ ] Sheet `Planos` exists with sheet param names and obligation flags
- [ ] Sheet `Proyecto` exists with ProjectInformation param names and flags
- [ ] No broken formulas or blank key columns
- [ ] All numeric values in correct format (no text in number fields)

**If any check fails:** ask the user to fix the Excel before running the audit.

---

## Resolving nomenclature errors — type renaming

**Never offer proactively to fix nomenclature errors.** After presenting the audit results, wait for the user to explicitly ask. They decide when and what to fix.

When the user asks to rename element types to fix nomenclature, **always use the same collector the auditor uses**:

```python
# CORRECT — matches the auditor query; returns ALL element types in the category
FilteredElementCollector(doc).OfCategory(bic).WhereElementIsElementType().ToElements()

# WRONG — filters by .NET class only; misses FamilySymbol and other ElementType
# subclasses that belong to the same category (e.g. Parapet Cap Bandstand)
FilteredElementCollector(doc).OfClass(WallType)
```

**Rule:** if the auditor finds a type as an error but your rename script didn't touch it, it means the two queries diverged. Always use `OfCategory(bic).WhereElementIsElementType()` for any rename or inspection that must be complete.

**After renaming, always re-run the audit** to confirm zero nomenclature errors remain before reporting the task as done.

### Anti-pattern: hardcoded ElementId map

**Never build a rename script with a hardcoded `{ElementId: new_name}` map.** This approach:
- Inflates the script to 100+ lines (triggering save-to-disk + `send_command_by_path`, which is wrong for one-off scripts)
- Is fragile — ElementIds change if the model is purged, saved-as, or elements are recreated
- Requires manual work to build the map instead of using the audit results

### Correct rename flow

1. The audit `ia_Result` already identifies which types fail nomenclature — use that data directly
2. Compute the correct name from the classification rules (`DISC_Category_Code_Description` pattern using `Disciplinas` + `Clasificaciones` sheets)
3. Rename by **current name**, not by ElementId
4. Keep the script to ~40-50 lines so it sends inline via `send_command` — no file save needed

**Rule:** `send_command_by_path` is only for production scripts run repeatedly (e.g. `ModelAudit.py`). One-off action scripts (rename, fix, export) must always be short enough for inline `send_command`. If a script grows too long, the problem is the design — fix the design, don't save it to disk.

```python
# Pattern: query types that fail, compute new name, rename by current name
for el in FilteredElementCollector(doc).OfCategory(bic).WhereElementIsElementType().ToElements():
    current = el.Name
    new_name = compute_correct_name(current, disc, classification)  # from audit rules
    if new_name and current != new_name:
        el.Name = new_name
```

---

## Common issues

| Symptom | Cause | Fix |
|---|---|---|
| Script fails immediately | Missing or malformed Excel sheet | Validate Excel format (see checklist above) |
| Score unrealistically high/low | Wrong Excel config for the model | Verify Excel has correct BEP values and rules |
| Parametros section empty | Matriz sheet missing BIC entries | Check Matriz sheet contains category rows |
| Nomenclatura shows no errors | Disciplinas/Clasificaciones incomplete | Verify both sheets have required code mappings |
| `NullReferenceException` in `WriteError` | `_actionResult` null before GIL block | Fixed in plugin — update to latest build |
| `_available_namespaces` crash on openpyxl | AcWebServices.dll init failure | Add guard or update plugin |
| Coordinate comparison always ERROR | Excel stores tenths of mm, not mm | Divide Excel value by 10 |
| `System` import fails with guard | Empty namespace dict blocks .NET hook | Don't import System; use BIC_MAP and Excel path for output |
| Rename script misses some types | Used `OfClass(X)` instead of `OfCategory(bic).WhereElementIsElementType()` | Always use the category-based query to match auditor coverage |

---

<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform -->
