# Skill: RevitApiPatterns

Reference guide for Revit API patterns on the PyNET platform. Read this skill whenever writing any script that queries, iterates, or measures elements in a Revit model.

> **Used by:** [QuantityTakeoff.md](QuantityTakeoff.md) · [QCModelAudit.md](QCModelAudit.md)

---

## Rule #1 — Query types directly, never through instances

**Always use `WhereElementIsElementType()` to get element types.** Never iterate instances and jump to their type via `GetTypeId()`.

```python
# CORRECT — direct type query, one step, no duplicates
wall_types = (FilteredElementCollector(doc)
    .OfCategory(BuiltInCategory.OST_Walls)
    .WhereElementIsElementType()
    .ToElements())

# WRONG — iterates 1,000+ instances to extract 30 types; wasteful and fragile
instances = FilteredElementCollector(doc).OfCategory(...).WhereElementIsNotElementType().ToElements()
for el in instances:
    type_el = doc.GetElement(el.GetTypeId())  # DON'T DO THIS to collect types
```

**Why it matters:** a model with 1,241 wall instances may have only 69 wall types. Using `WhereElementIsElementType()` queries 69 objects directly — not 1,241. Using `GetTypeId()` on instances also produces duplicates that must be de-duped, adding unnecessary complexity.

**When to use instances (`WhereElementIsNotElementType()`):** only when you need instance-level data — geometry, location, level, or instance parameters. For type names, family names, or type parameters: always query types directly.

---

## Rule #2 — ElementId in Revit 2024+

In Revit 2024+ `ElementId.IntegerValue` (Int32) no longer exists. Use `ElementId.Value` (Int64).

```python
# CORRECT — works in Revit 2024+
type_id = int(type_el.Id.Value)

# WRONG — raises AttributeError in Revit 2024+
type_id = type_el.Id.IntegerValue
```

For compatibility across versions:
```python
def eid_val(eid):
    try:
        return int(eid.Value)         # Revit 2024+
    except AttributeError:
        return int(eid.IntegerValue)  # older versions
```

---

## Getting family name and type name

```python
type_els = (FilteredElementCollector(doc)
    .OfCategory(BuiltInCategory.OST_Walls)
    .WhereElementIsElementType()
    .ToElements())

for t in type_els:
    type_name = t.Name or ""
    family_name = ""
    fp = t.get_Parameter(BuiltInParameter.ALL_MODEL_FAMILY_NAME)
    if fp:
        family_name = fp.AsString() or ""
    type_id = int(t.Id.Value)
```

---

## Counting instances per type

When you need both the type data and the instance count, query types first then build a count from instances:

```python
# Step 1: collect types
type_map = {}
for t in (FilteredElementCollector(doc)
        .OfCategory(bic)
        .WhereElementIsElementType()
        .ToElements()):
    type_map[int(t.Id.Value)] = {"name": t.Name, "count": 0}

# Step 2: count instances (only when count is needed)
for el in (FilteredElementCollector(doc)
        .OfCategory(bic)
        .WhereElementIsNotElementType()
        .ToElements()):
    tid = int(el.GetTypeId().Value)
    if tid in type_map:
        type_map[tid]["count"] += 1
```

---

## Area measurements by category

Areas come from built-in parameters. Units are **square feet** — multiply by `0.0929` to get m².

> ⚠️ `WALL_ATTR_AREA_PARAM` does **NOT** exist in Revit 2024+. Walls are measured in ml via `CURVE_ELEM_LENGTH`, not m².

| Category | Unit | BuiltInParameter | Conversion |
|---|---|---|---|
| Walls | ml | `CURVE_ELEM_LENGTH` | ft × 0.3048 |
| Floors | m² | `HOST_AREA_COMPUTED` | ft² × 0.0929 |
| Ceilings | m² | `HOST_AREA_COMPUTED` | ft² × 0.0929 |
| Roofs | m² | `HOST_AREA_COMPUTED` | ft² × 0.0929 |

```python
FT2_TO_M2 = 0.0929
FT_TO_M   = 0.3048

# Wall length (ml)
p = el.get_Parameter(BuiltInParameter.CURVE_ELEM_LENGTH)
length_m = round(p.AsDouble() * FT_TO_M, 2) if p and p.HasValue else 0.0

# Floor / ceiling / roof area (m²)
p = el.get_Parameter(BuiltInParameter.HOST_AREA_COMPUTED)
area_m2 = round(p.AsDouble() * FT2_TO_M2, 3) if p and p.HasValue else 0.0
```

**Note:** area parameters live on **instances**, not types. To get total area per type, iterate instances and accumulate.

---

## Count-based measurements

For doors, windows, luminaries, furniture, etc. — each instance counts as 1 unit. No parameter needed.

```python
# Count instances per type
instances = (FilteredElementCollector(doc)
    .OfCategory(BuiltInCategory.OST_Doors)
    .WhereElementIsNotElementType()
    .ToElements())

count_by_type = {}
for el in instances:
    tid = int(el.GetTypeId().Value)
    count_by_type[tid] = count_by_type.get(tid, 0) + 1
```

---

## Category → BuiltInCategory map (common)

```python
BIC_MAP = {
    "Muros":                  BuiltInCategory.OST_Walls,
    "Suelos":                 BuiltInCategory.OST_Floors,
    "Techos":                 BuiltInCategory.OST_Ceilings,
    "Cubiertas":              BuiltInCategory.OST_Roofs,
    "Puertas":                BuiltInCategory.OST_Doors,
    "Ventanas":               BuiltInCategory.OST_Windows,
    "Pilares estructurales":  BuiltInCategory.OST_StructuralColumns,
    "Armazón estructural":    BuiltInCategory.OST_StructuralFraming,
    "Luminarias":             BuiltInCategory.OST_LightingFixtures,
    "Aparatos sanitarios":    BuiltInCategory.OST_PlumbingFixtures,
    "Escaleras":              BuiltInCategory.OST_Stairs,
    "Barandillas":            BuiltInCategory.OST_Railings,
    "Mobiliario":             BuiltInCategory.OST_Furniture,
    "Equipos mecánicos":      BuiltInCategory.OST_MechanicalEquipment,
    "Conductos":              BuiltInCategory.OST_DuctCurves,
    "Tuberías":               BuiltInCategory.OST_PipeCurves,
}
```

---

## Reading / writing type parameters

```python
# Read a type parameter (string)
param = type_el.LookupParameter("MyParam")
val = param.AsString() if param and param.HasValue else ""

# Write a type parameter — requires transaction
t = Transaction(doc, "Set param")
t.Start()
try:
    param = type_el.LookupParameter("MyParam")
    if param and not param.IsReadOnly:
        param.Set("new_value")
    t.Commit()
except:
    t.RollBack()
    raise
```

---

## Exporting to Excel (openpyxl)

Hard-won rules — ignoring any of these turns a sub-second export into minutes, or produces a file Excel refuses to open ("Hemos encontrado un problema con el contenido…").

**1. NEVER auto-fit column widths with `ws.columns`.** It is the #1 performance trap: each access walks every cell of the sheet, so on a few thousand styled rows it takes *minutes* (measured: 210s on one audit). Just don't set widths — the user auto-fits with a double-click. If you really need widths, track the max length *while appending rows*, never via `ws.columns`.

```python
# WRONG — O(n²), can take minutes
for col in ws.columns:
    ws.column_dimensions[col[0].column_letter].width = min(max(len(str(c.value or '')) for c in col)+2, 60)

# RIGHT — don't set widths at all (user auto-fits), or track inline while appending
```

**2. Use a real Excel Table, and NEVER name it like a cell reference.** `displayName="T1"` corrupts the file silently — Excel reads `T1` as cell T1 and rejects the table. Use a name that can't be a cell reference (`Tabla_1`, `tbl_data`).

```python
from openpyxl.worksheet.table import Table, TableStyleInfo
ti = 0
for sec, rows in results.items():
    ws = wb.create_sheet(sec[:31])
    ws.append(['Check', 'Estado', 'Detalle', 'ElementId'])
    for r in rows:
        ws.append([r['Check'] or None, r['Estado'] or None, r['Detalle'] or None, r['ElementId'] or None])
    if rows:
        ti += 1
        tbl = Table(displayName=f'Tabla_{ti}', ref=f'A1:D{ws.max_row}')   # NOT f'T{ti}'
        tbl.tableStyleInfo = TableStyleInfo(name='TableStyleMedium2', showRowStripes=True)
        ws.add_table(tbl)
```

**3. Write empty values as `None`, never `''`.** An empty string becomes an invalid `<c t="inlineStr"></c>` cell (no `<is>`), which Excel flags as corrupt content. Coerce with `value or None` when appending.

**4. Debugging a "corrupt" xlsx:** an `.xlsx`/`.docx`/`.pptx` is just a **ZIP of XML**. Rename to `.zip` (or `unzip -l`) and inspect `xl/worksheets/sheet*.xml`, `xl/tables/table*.xml`, `[Content_Types].xml`. A sheet that is suddenly MBs in size = a runaway row count; check the table `ref` and the sheet `<dimension>`.

---

## Common pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| 0 types found despite elements existing | Used `WhereElementIsNotElementType()` when querying types | Switch to `WhereElementIsElementType()` |
| `AttributeError: ElementId has no attribute IntegerValue` | Revit 2024+ | Use `eid.Value` |
| Area returns 0 | Parameter queried on type, not instance | Area BIPs live on instances |
| Type map empty after iteration | `GetTypeId()` returning null element | Always check `type_el is not None` |
| Excel export takes minutes | Auto-fitting widths via `ws.columns` | Don't set widths; user auto-fits |
| "Problema con el contenido" on open | Table `displayName` looks like a cell ref (`T1`) | Use `Tabla_1` / non-reference name |
| "Problema con el contenido" on open | Empty cells written as `''` (invalid `inlineStr`) | Write `value or None` |

---

<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform -->
