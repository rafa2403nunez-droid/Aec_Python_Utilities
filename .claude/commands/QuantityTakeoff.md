# Skill: QuantityTakeoff

5D budget extraction workflow for Revit models on the PyNET platform. Reads a reference Excel with resource codes, extracts quantities from the model, and generates a measurement breakdown Excel + interactive HTML report with charts.

> **Read first:** [RevitApiPatterns.md](RevitApiPatterns.md) — all element/type querying patterns used here follow those rules.

---

## Context

- **Host:** Revit only (uses `__revit__` global)
- **Parameters in model:** `{PREFIX}_5D_CodigoRecurso`, `{PREFIX}_5D_CapituloPresupuesto`, `{PREFIX}_5D_CosteUnitario`, `{PREFIX}_5D_Proveedor` — bound to all main architectural and MEP categories

  > ⚠️ **The prefix is project-specific — always ask the user for it before running.** It is defined in the project's MIDP (Master Information Delivery Plan). Examples seen: `PyNET_` (default platform prefix), `Test_` (dev/testing). Never hardcode a prefix — the user will provide it at the start of each session.
- **Reference Excel:** `5D_Recursos_Referencia.xlsx` on the user's Desktop
- **Production script:** `01_Scripts/02_Revit/26_5D/QuantityTakeoff.py` — always run via `send_command_by_path`
- **Output:** Desktop `5D_Presupuesto_<YYYYMMDD_HHMMSS>.xlsx` + `.html` — both opened automatically

---

## Reference Excel structure

File: `5D_Recursos_Referencia.xlsx` (Desktop)

| Column | Description |
|---|---|
| `CodigoRecurso` | BEDEC-style code — 8 chars, e.g. `E612B11K` |
| `Capitulo` | Budget chapter (one of 6 standard chapters) |
| `Descripcion` | Human-readable description in Spanish |
| `Unidad` | `ml` for walls · `m²` for floors/ceilings/roofs · `ud` for count |
| `PrecioUnitario` | Unit price in € |
| `RevitCategoria` | Revit category name in Spanish (e.g. `Muros`) |
| `RevitTipoFamilia` | **Exact** Revit type name — must match `type_el.Name` character-for-character |

Matching key: `(RevitCategoria, RevitTipoFamilia)` → resource definition.

### Standard chapters and colors

| Chapter | HTML color |
|---|---|
| Cerramientos | `#2980b9` |
| Forjados y Pavimentos | `#27ae60` |
| Techos | `#c9a227` |
| Carpintería | `#e67e22` |
| Instalaciones Eléctricas | `#8e44ad` |
| Instalaciones Sanitarias | `#c0392b` |

### BEDEC code convention

8-character codes following ITEC BEDEC format:
- `E6xxxx` — cerramientos y particiones
- `E45xxx` — forjados de hormigón
- `E9Cxxx` — pavimentos
- `E84xxx` — techos
- `EAFxxx` — carpintería puertas
- `EC1xxx` — carpintería ventanas
- `EG6xxx` — luminarias
- `EJ1xxx` — aparatos sanitarios

---

## Measurement rules

> ⚠️ **Critical:** `WALL_ATTR_AREA_PARAM` does NOT exist in Revit 2024+. All area-based categories use `HOST_AREA_COMPUTED`. Walls are measured in **ml** (metros lineales) via `CURVE_ELEM_LENGTH`.

| Category | Unit | BIP | Conversion |
|---|---|---|---|
| Muros | ml | `CURVE_ELEM_LENGTH` | ft × 0.3048 |
| Suelos | m² | `HOST_AREA_COMPUTED` | ft² × 0.0929 |
| Techos | m² | `HOST_AREA_COMPUTED` | ft² × 0.0929 |
| Cubiertas | m² | `HOST_AREA_COMPUTED` | ft² × 0.0929 |
| Puertas | ud | — | count = 1 per instance |
| Ventanas | ud | — | count = 1 per instance |
| Luminarias | ud | — | count = 1 per instance |
| Aparatos sanitarios | ud | — | count = 1 per instance |

Area/length parameters live on **instances**, not types. Always query instances for quantities.

---

## Workflow

### 1. Check active instance
```python
list_active_instances  # must be Revit
```

### 2. Verify reference Excel exists
Default path: Desktop `5D_Recursos_Referencia.xlsx`. If it doesn't exist, create it (see "Creating the reference Excel" section). If it exists but locked (Permission denied), ask the user to close it in Excel first.

### 3. Run the production script
```python
send_command_by_path(
    pid=<pid>,
    script_name="QuantityTakeoff",
    file_path=r"C:\Users\34655\source\repos\GithubRNM\PyNetLibrary\01_Scripts\02_Revit\26_5D\QuantityTakeoff.py",
    timeout=120
)
```

The script:
1. Loads the reference Excel → builds lookup `{(categoria, tipo): resource_def}`
2. Queries element **types** per category with `WhereElementIsElementType()` → matches to lookup
3. Iterates **instances** to accumulate measurements (length/area/count) per resource, storing every ElementId
4. Writes Excel: sheet **Mediciones** (chapter headers → partida rows → element breakdown → total) + sheet **Resumen**
5. Writes HTML: header with grand total, KPI row, donut chart, bar chart, chapter cards, collapsible partidas with element-level breakdown
6. Opens HTML in browser automatically

### 4. Report results
Present chapter summary and grand total. HTML opens automatically.

---

## Excel output structure

### Sheet: Mediciones

```
CERRAMIENTOS (chapter header, dark color, spans 5 cols, total on col 6)
  E612B11K | Partición interior GWB 4 7/8" | ml | 35.50 | 85.00 | 3.017,50 €  ← partida (bold)
    1234567 |                               |    |  8.23 |       |              ← element row
    2345678 |                               |    | 12.45 |       |
    ...
  (blank row between partidas)
TOTAL PRESUPUESTO (dark row, col 6 = grand total)
```

### Sheet: Resumen

| Capítulo | Total (€) | % s/Total |
Color-coded rows + grand total.

---

## HTML output structure

Single-file self-contained HTML (no external dependencies):

| Section | Content |
|---|---|
| **Header** | Model name · date · grand total (top right, large) |
| **KPIs** | Total €, Capítulos, Partidas, Elementos medidos |
| **Donut chart** | SVG multi-segment, one segment per chapter |
| **Bar chart** | Horizontal bars, € per chapter |
| **Chapter cards** | Clickable, scroll to chapter detail |
| **Detail** | Per chapter → collapsible partidas → ElementID table with total row at bottom |

The donut uses multi-segment SVG (one `<circle>` per chapter with cumulative `stroke-dashoffset`). Circumference = 2π×16 ≈ 100.53. Start offset = C/4 (top).

---

## Core script pattern

```python
FT2_TO_M2 = 0.0929
FT_TO_M   = 0.3048
AREA_CATS   = {"Suelos", "Techos", "Cubiertas"}
LENGTH_CATS = {"Muros"}

# Step 1: build lookup from Excel
resource_lookup = {}  # (categoria, tipo) -> {code, capitulo, desc, unit, price}

# Step 2: resolve types → resource, accumulate instances
budget = {}  # code -> {meta..., qty, elements: [{eid, qty}]}

for cat_name, bic in BIC_MAP.items():
    type_code_map = {}
    for t in FilteredElementCollector(doc).OfCategory(bic).WhereElementIsElementType().ToElements():
        res = resource_lookup.get((cat_name, (t.Name or "").strip()))
        if res:
            type_code_map[int(t.Id.Value)] = res   # Revit 2024+: use .Value not .IntegerValue

    for el in FilteredElementCollector(doc).OfCategory(bic).WhereElementIsNotElementType().ToElements():
        tid = int(el.GetTypeId().Value)
        res = type_code_map.get(tid)
        if not res: continue
        code = res["code"]
        if code not in budget:
            budget[code] = {**res, "qty": 0.0, "elements": []}

        if cat_name in LENGTH_CATS:
            p = el.get_Parameter(BuiltInParameter.CURVE_ELEM_LENGTH)
            qty = round(p.AsDouble() * FT_TO_M, 2) if p and p.HasValue else 0.0
        elif cat_name in AREA_CATS:
            p = el.get_Parameter(BuiltInParameter.HOST_AREA_COMPUTED)
            qty = round(p.AsDouble() * FT2_TO_M2, 2) if p and p.HasValue else 0.0
        else:
            qty = 1.0

        budget[code]["qty"] += qty
        budget[code]["elements"].append({"eid": int(el.Id.Value), "qty": qty})
```

---

## Creating the reference Excel

If the reference Excel doesn't exist, create it via `send_command`:

1. Query types per category with `WhereElementIsElementType()` — collect family name + type name
2. Assign BEDEC-style codes, chapters, units and realistic prices
3. Save with openpyxl, color-coded by chapter, to `Desktop/5D_Recursos_Referencia.xlsx`

```python
# Key price references (€) used in this project
# ml: walls 70–220 (by type)   m²: floors 45–110, ceilings 50–70
# ud: doors 680–950, windows 480–650, lights 180–320, sanitary 280–450
```

If the user wants to update a unit (e.g. change walls from m² to ml), update column D in the Excel and reload the script — no code changes needed.

---

## Populating model parameters — two-phase workflow

Parameters are filled in two phases. **Both phases require user confirmation** (write operations).

### Phase 1 — Fill `{PREFIX}_5D_CodigoRecurso` (run before budget review)

Only the resource code is written to types at this stage — it links the model to the reference Excel and enables downstream use (IFC export, schedules, Navisworks).

```python
# PREFIX = ask the user — defined in project MIDP (e.g. "PyNET_", "ARQ_", etc.)
t = Transaction(doc, f"Fill {PREFIX}5D_CodigoRecurso")
t.Start()
try:
    filled = 0
    for cat_name, bic in BIC_MAP.items():
        for type_el in FilteredElementCollector(doc).OfCategory(bic).WhereElementIsElementType().ToElements():
            res = resource_lookup.get((cat_name, (type_el.Name or "").strip()))
            if not res: continue
            p = type_el.LookupParameter(f"{PREFIX}5D_CodigoRecurso")
            if p and not p.IsReadOnly:
                p.Set(res["code"])
                filled += 1
    t.Commit()
    print(f"Filled {PREFIX}5D_CodigoRecurso on {filled} types")
except:
    t.RollBack()
    raise
```

### Phase 2 — Fill remaining parameters (run after budget review)

Once the user has reviewed and approved the budget, fill chapter, unit cost and supplier on the types:

```python
# CosteUnitario is NUMBER type — use float(), not str()
for param_name, key, as_float in [
    (f"{PREFIX}5D_CapituloPresupuesto", "capitulo", False),
    (f"{PREFIX}5D_CosteUnitario",       "price",    True),
]:
    p = type_el.LookupParameter(param_name)
    if p and not p.IsReadOnly:
        p.Set(float(res[key]) if as_float else str(res[key]))
```

---

## Common issues

| Symptom | Cause | Fix |
|---|---|---|
| 0 resources matched | Type name in Excel doesn't match model exactly | Run a type discovery script: `WhereElementIsElementType()` + print `t.Name` per category |
| `Permission denied` on Excel | File open in Excel | Ask user to close it |
| Area returns 0 | `WALL_ATTR_AREA_PARAM` doesn't exist | Use `HOST_AREA_COMPUTED` for area, `CURVE_ELEM_LENGTH` for length |
| `AttributeError: IntegerValue` | Revit 2024+ | Use `el.Id.Value` (Int64) |
| openpyxl import fails | `_available_namespaces` session error | Retry once; if persists, restart Revit |
| Type map empty (0 types) | Used `WhereElementIsNotElementType()` | Switch to `WhereElementIsElementType()` |

---

<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform -->
