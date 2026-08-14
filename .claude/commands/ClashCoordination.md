# Skill: ClashCoordination

Start the conversation in english. If the user request to change you can use the user language.

Cross-application coordination workflow: reads **Reviewed** clash results from Navisworks and creates the corresponding floor openings in Revit.

> **Always read [ClashDetection.md](ClashDetection.md) alongside this skill.** It contains the full Navisworks API patterns, CastUtils boilerplate, iteration helpers, property reading utilities, and clash approval criteria that this workflow depends on.

---

## Context

- Two active PyNET instances are required: one in **Navisworks** and one in **Revit**
- Use `list_active_instances` to identify both PIDs before starting
- Navisworks coordinates and Revit internal coordinates share the same origin when the model was exported with shared coordinates — always verify by comparing a known floor Z with `bb.Min.Z * 304.8`
- Revit API uses **feet** internally — always convert with `mm / 304.8`
- `StructuralType` is in `Autodesk.Revit.DB.Structure`, not in the main `Autodesk.Revit.DB` namespace — always import it explicitly

### Revit boilerplate

```python
import clr
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Structure import StructuralType
from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document
```

---

## Workflow

### 1. Verify active instances and cross-check source files

```python
# list_active_instances → get Navisworks PID and Revit PID
```

**Before doing anything else, verify that the Revit document matches the NWC source.** The `"Archivo de origen"` property in the `"Elemento"` category of any clash item contains the `.rvt` filename the NWC was exported from. Compare it against the active Revit document name to confirm you are writing to the correct model.

Read it from Navisworks by walking up to the instance node (same `.Parent` traversal used for element IDs):

```python
def get_source_file(item):
    node = item
    for _ in range(6):
        for cat in node.PropertyCategories:
            if cat.DisplayName == "Elemento":
                for prop in cat.Properties:
                    if prop.DisplayName == "Archivo de origen":
                        try:
                            return prop.Value.ToDisplayString()
                        except:
                            return None
        if node.Parent is None:
            break
        node = node.Parent
    return None

# Sample any clash item — Item1 or Item2 both carry the property
first_test = next(iter(testsData.Value.TestsRoot.Children))
first_result = next(iter_all_results(first_test))
nwc_source = get_source_file(first_result.Item1) or get_source_file(first_result.Item2)
```

Then in Revit get the active document filename and compare:

```python
from pathlib import Path
revit_filename = Path(doc.PathName).name if doc.PathName else doc.Title + ".rvt"

if nwc_source and Path(nwc_source).stem.lower() != Path(revit_filename).stem.lower():
    raise RuntimeError(
        f"Source file mismatch: NWC was exported from '{nwc_source}' "
        f"but active Revit document is '{revit_filename}'. "
        f"Open the correct Revit file before proceeding."
    )
```

> **This check is mandatory.** Placing openings in the wrong Revit model is a silent error that can corrupt coordination work. Never skip it. In federated models with multiple NWCs, sample `Item2` (the structural/architectural host) specifically, as `Item1` (MEP) may come from a different source file.

### 2. Read Reviewed clashes from Navisworks

Use the CastUtils + DocumentClash pattern from ClashDetection. Filter by `ClashResultStatus.Reviewed` and collect position + geometry for each result:

```python
def iter_all_results(test):
    for child in test.Children:
        if child.IsGroup:
            for r in child.Children:
                yield r
        else:
            yield child

def ft_to_mm(ft):
    return round(ft * 304.8, 1)

def bbox_to_dict(bb):
    return {
        "min": {"x": ft_to_mm(bb.Min.X), "y": ft_to_mm(bb.Min.Y), "z": ft_to_mm(bb.Min.Z)},
        "max": {"x": ft_to_mm(bb.Max.X), "y": ft_to_mm(bb.Max.Y), "z": ft_to_mm(bb.Max.Z)},
        "size_x": ft_to_mm(bb.Max.X - bb.Min.X),
        "size_y": ft_to_mm(bb.Max.Y - bb.Min.Y),
    }

results = []
for test in testsData.Value.TestsRoot.Children:
    for result in iter_all_results(test):
        if result.Status != ClashResultStatus.Reviewed:
            continue
        center = result.Center
        results.append({
            "test": test.DisplayName,
            "clash": result.DisplayName,
            "center_mm": {"x": ft_to_mm(center.X), "y": ft_to_mm(center.Y), "z": ft_to_mm(center.Z)},
            "item1_bbox": bbox_to_dict(result.Item1.BoundingBox()),
            "item2_bbox": bbox_to_dict(result.Item2.BoundingBox()),
            "comments": [c.Body for c in result.Comments] if result.Comments else [],
        })
```

### 3. Get Revit element IDs from Navisworks

Each clash item is a geometry solid node. Walk up via `.Parent` to reach the instance node, which contains the **"ID de elemento"** property category with the Revit element ID.

```python
def safe_val(v):
    try:
        if v.IsDisplayString: return v.ToDisplayString()
        dt = str(v.DataType)
        if "Int32" in dt: return str(v.ToInt32(None))
        if "Double" in dt: return str(v.ToDouble(None))
        return dt
    except:
        return "?"

def get_revit_element_id(item):
    node = item
    for _ in range(6):  # max 6 levels up
        for cat in node.PropertyCategories:
            if cat.DisplayName == "ID de elemento":
                for prop in cat.Properties:
                    return safe_val(prop.Value)
        if node.Parent is None:
            break
        node = node.Parent
    return None
```

**Use this to get the host floor ID directly** — no need to run a collector in Revit.

### 4. Analyse comments and determine opening type

Read the comments on each Reviewed clash to identify what coordination action is required. Look specifically for keywords like "apertura", "hueco", "coordinada" to detect opening cases.

**Opening type decision rules:**

| MEP element | Condition | Opening type |
|---|---|---|
| Circular pipe (TUB) | No nearby MEP within 1000mm | `Hueco_Suelos_Circular` |
| Circular pipe (TUB) | Another MEP (CON or TUB) within 1000mm | `Hueco_Suelos` (shared rectangular) |
| Rectangular duct (CON) | Always | `Hueco_Suelos` (rectangular) |

**Proximity check** — always compute 3D distance between clash centers before deciding:

```python
import math

def clash_distance_mm(c1, c2):
    return math.sqrt((c1["x"]-c2["x"])**2 + (c1["y"]-c2["y"])**2 + (c1["z"]-c2["z"])**2)
```

> **Critical rule:** If a TUB clash and a CON clash are within 1000mm of each other on the same floor zone, they must share a **single rectangular hole**. Do NOT create a circular hole for the pipe. The comments from the clash review session will explicitly mention the distance to the nearby element — read them carefully.

### 5. Calculate opening dimensions

#### Rectangular opening (single element)
- Width (X) = element bbox size_x + 100mm (50mm clearance each side)
- Length (Y) = element bbox size_y + 100mm

#### Rectangular opening (shared — multiple elements)
Use the combined bounding box of all involved elements:

```python
# Left edge = min of all bbox min.x values
# Right edge = max of all bbox max.x values
# Same for Y
combined_min_x = min(e["bbox"]["min"]["x"] for e in elements)
combined_max_x = max(e["bbox"]["max"]["x"] for e in elements)
combined_min_y = min(e["bbox"]["min"]["y"] for e in elements)
combined_max_y = max(e["bbox"]["max"]["y"] for e in elements)

width_mm  = (combined_max_x - combined_min_x) + 100.0
length_mm = (combined_max_y - combined_min_y) + 100.0

center_x = (combined_min_x + combined_max_x) / 2.0
center_y = (combined_min_y + combined_max_y) / 2.0
```

#### Circular opening
- Radius = (pipe OD / 2) + 50mm clearance
- Pipe OD = bbox size_x (the bounding box of a vertical circular pipe has equal X and Y matching the outer diameter)

### 6. Identify opening families in Revit

#### 6a. Check prior history first

Before asking the user, check if this model has been coordinated before:
- Search AI History responses for previous `PlaceHuecos` or similar scripts on the same Revit PID
- Check memory for any recorded family names for this project

If a validated family name is found in history → use it directly and skip the user question.

#### 6b. If no history — discover available families and ask the user

Run a quick scan to list all floor-hosted generic model families loaded in the document:

```python
all_families = FilteredElementCollector(doc).OfClass(Family).ToElements()
floor_opening_candidates = []
for f in all_families:
    if f.FamilyCategory and "Modelo genérico" in f.FamilyCategory.Name:
        syms = [doc.GetElement(sid).Name for sid in f.GetFamilySymbolIds()]
        floor_opening_candidates.append({"family": f.Name, "symbols": syms})
# Also include families with "hueco", "opening", "sleeve", "pasatubos" in the name (case-insensitive)
keyword_candidates = [f.Name for f in all_families
                      if any(k in f.Name.lower() for k in ["hueco", "opening", "sleeve", "pasatubos", "pase"])]
```

Present the candidates to the user and ask:

> "I need to know which families to use for floor openings. I found these candidates in the model: **[list]**. Which one should I use for rectangular openings, and which for circular ones? If they don't exist yet, tell me the names and I'll confirm they're loaded before proceeding."

**Do not proceed to placement until the user has confirmed both family names** (rectangular and circular). Record them for the rest of the session.

#### 6c. Guard: confirm the active document is a project, not a family

Always check this before any Revit operation. If the user has an RFA open and active, `__revit__.ActiveUIDocument.Document` will be a family document and collectors/placement will either fail or target the wrong context.

```python
uidoc = __revit__.ActiveUIDocument
doc = uidoc.Document

if doc.IsFamilyDocument:
    raise RuntimeError(
        "Active document is a Family (RFA), not a project. "
        "Switch to the project document in Revit before running this script."
    )
```

#### 6d. Inspect family parameters via FamilyManager (no test instances needed)

Once the family is found in the project, open it with `EditFamily` and read parameters directly from `FamilyManager.Parameters`. This is the correct approach — **never place test instances just to discover parameters**.

```python
results = {}
for f in all_families:
    if f.Name not in (RECT_FAMILY_NAME, CIRC_FAMILY_NAME):
        continue
    family_doc = doc.EditFamily(f)
    try:
        mgr = family_doc.FamilyManager
        params = []
        for p in mgr.Parameters:
            params.append({
                "name": p.Definition.Name,
                "is_instance": p.IsInstance,
            })
        results[f.Name] = params
    finally:
        family_doc.Close(False)  # always close — use finally to guarantee it even on error
```

> **`ParameterGroup` / `ParameterType` are not available on `InternalDefinition`** in Revit 2024+. Only use `p.Definition.Name` and `p.IsInstance`.

> **Always use `try/finally`** around `EditFamily` so the family document is closed even if an exception occurs. Leaving it open causes the next `EditFamily` call on the same family to fail.

Focus on parameters where `is_instance == True` — those are settable per placement without duplicating types.

#### 6e. Load symbols

```python
all_families = FilteredElementCollector(doc).OfClass(Family).ToElements()
hueco_rect_sym = None
hueco_circ_sym = None
for f in all_families:
    if f.Name == RECT_FAMILY_NAME:
        hueco_rect_sym = doc.GetElement(list(f.GetFamilySymbolIds())[0])
    if f.Name == CIRC_FAMILY_NAME:
        hueco_circ_sym = doc.GetElement(list(f.GetFamilySymbolIds())[0])

if not hueco_rect_sym or not hueco_circ_sym:
    raise RuntimeError("Family not found in document. Load it first.")
```

**Family names confirmed in ModeloR project:** `Hueco_Suelos` (rectangular) and `Hueco_Suelos_Circular`.

**Instance parameters:**

| Family | Parameter | Type | Description |
|---|---|---|---|
| Hueco_Suelos | `Ancho` | Double (ft) | Width |
| Hueco_Suelos | `Largo` | Double (ft) | Length |
| Hueco_Suelos | `Alto_Superior` | Double (ft) | Extension above floor |
| Hueco_Suelos | `Alto_Inferior` | Double (ft) | Extension below floor (≥ floor thickness) |
| Hueco_Suelos_Circular | `Radio` | Double (ft) | Hole radius |
| Hueco_Suelos_Circular | `Alto_Superior` | Double (ft) | Extension above floor |
| Hueco_Suelos_Circular | `Alto_Inferior` | Double (ft) | Extension below floor |

**Recommended depth values:**
- `Alto_Superior` = 25mm (slight margin above floor top face)
- `Alto_Inferior` = floor thickness + 25mm

### 7. Get the host floor element in Revit

Use the Revit element ID obtained from Navisworks (step 3) directly — no collector needed:

```python
floor = doc.GetElement(ElementId(revit_floor_id))
```

### 8. Read MEP element rotation from Revit

For rectangular ducts and pipes, the cross-section may be rotated in XY. The rotation must be read from the Revit MEP element (using its Revit ID obtained from Navisworks in step 3) and applied to the placed hole so it aligns correctly.

**Always check rotation for every MEP element before placing its hole. Always read it from the live Revit model — never from the Navisworks geometry.** The NWC may be stale: the Revit model can be modified (element rotated, resized, moved) after the last NWC export without regenerating it. The Navisworks bbox will reflect the old state while Revit holds the current truth. The Revit connector's `BasisX` is the only authoritative source for cross-section orientation.

The rotation is not a simple parameter — it lives in the connector's `CoordinateSystem.BasisX`. Use `atan2(BasisX.Y, BasisX.X)` to get the angle in the XY plane:

```python
import math
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *

def get_mep_rotation_deg(document, revit_element_id):
    elem = document.GetElement(ElementId(revit_element_id))
    if elem is None:
        return 0.0
    try:
        cm = elem.ConnectorManager
        for conn in cm.Connectors:
            bx = conn.CoordinateSystem.BasisX
            return math.degrees(math.atan2(bx.Y, bx.X))
    except:
        pass
    # Fallback: LocationCurve direction projected to XY
    loc = elem.Location
    if isinstance(loc, LocationCurve):
        d = loc.Curve.Direction
        if abs(d.Z) < 0.999:  # not purely vertical
            return math.degrees(math.atan2(d.Y, d.X))
    return 0.0
```

For shared holes (multiple elements), use the rotation of the dominant element (the duct, not the pipe).

### 9. Place and configure instances

```python
import math

def mm_to_ft(mm):
    return mm / 304.8

t = Transaction(doc, "Colocar Huecos de Coordinacion")
t.Start()
try:
    for sym in [hueco_rect_sym, hueco_circ_sym]:
        if sym and not sym.IsActive:
            sym.Activate()
    doc.Regenerate()

    for hole in holes_to_create:
        pt = XYZ(mm_to_ft(hole["x"]), mm_to_ft(hole["y"]), 0.0)
        inst = doc.Create.NewFamilyInstance(pt, hole["symbol"], floor, StructuralType.NonStructural)

        for param_name, val_mm in hole["params"].items():
            p = inst.LookupParameter(param_name)
            if p and not p.IsReadOnly:
                p.Set(mm_to_ft(val_mm))

        # Apply MEP element rotation so the hole aligns with the element cross-section
        rotation_deg = hole.get("rotation_deg", 0.0)
        if abs(rotation_deg) > 0.01:
            axis = Line.CreateBound(pt, XYZ(pt.X, pt.Y, pt.Z + 1))
            ElementTransformUtils.RotateElement(doc, inst.Id, axis, math.radians(rotation_deg))

    t.Commit()
except Exception as e:
    t.RollBack()
    raise
```

Each entry in `holes_to_create` should include `"rotation_deg"` populated from `get_mep_rotation_deg()` in step 8. Circular holes don't need rotation — only rectangular ones.

### 10. Update existing holes after design changes

When the MEP design changes (element moved, resized, or rotated), existing holes need to be updated — not recreated. The Revit element ID of the hole is stable across sessions; retrieve it from the AI History response of the original placement script.

For each affected hole, re-read the MEP element state from Revit and apply the delta:

**Reposition:**
```python
inst = doc.GetElement(ElementId(hole_revit_id))
new_pt = XYZ(mm_to_ft(new_x_mm), mm_to_ft(new_y_mm), 0.0)
inst.Location.Move(new_pt - inst.Location.Point)
```

**Resize:**
```python
inst.LookupParameter("Ancho").Set(mm_to_ft(new_width_mm))
inst.LookupParameter("Largo").Set(mm_to_ft(new_length_mm))
```

**Re-rotate** (rotation is cumulative — reset by applying the inverse of the current rotation first, then the new one; or use `GetTransform` to read current angle):
```python
# Simplest: rotate by the delta angle
delta_rad = math.radians(new_rotation_deg - current_rotation_deg)
axis = Line.CreateBound(inst.Location.Point, XYZ(inst.Location.Point.X, inst.Location.Point.Y, inst.Location.Point.Z + 1))
ElementTransformUtils.RotateElement(doc, inst.Id, axis, delta_rad)
```

Always re-read `get_mep_rotation_deg()` from the live Revit element — never assume the previous value is still valid.

### 11. Present summary and ask for visual verification

After placement, report a summary table to the user:

| # | Family | Position (mm) | Dimension | Covers |
|---|---|---|---|---|
| ID | Hueco_Suelos | (x, y) | WxL mm | Element names |

Ask the user to verify in Revit that:
1. Each hole is visually centered on its element(s)
2. The Ancho/Largo orientation matches the element direction
3. Alto_Inferior fully penetrates the floor

---

## Key lessons learned

- **Geometry nodes vs instance nodes:** Clash result `Item1`/`Item2` point to geometry solid nodes. The Revit element ID is NOT there — it is at the parent instance node. Always walk up via `.Parent` to find `"ID de elemento"`.
- **One floor, multiple z-values:** A single thick floor will generate clash results at both its top face (z=0) and bottom face (z=−thickness). These are the SAME element — deduplicate by Revit element ID before creating holes.
- **Shared holes:** When the clash comments mention a nearby MEP element, or when `clash_distance_mm` < 1000mm between a TUB and CON clash on the same floor zone, always use a single shared rectangular hole — never individual holes. Failing to do this is the most common mistake.
- **Family names:** The actual families in this project are `Hueco_Suelos` and `Hueco_Suelos_Circular` (with trailing "s"). Always confirm family names with `FilteredElementCollector(doc).OfClass(Family)` before assuming.
- **StructuralType import:** Must be imported from `Autodesk.Revit.DB.Structure` explicitly — it is not included in the `from Autodesk.Revit.DB import *` wildcard.
- **Duct rotation — always read from Revit, never from Navisworks:** The NWC can be stale — a duct may have been rotated in Revit after the last export without regenerating the NWC. The Navisworks bbox reflects the old geometry while Revit holds the current state. Always call `get_mep_rotation_deg()` on the live Revit element and apply the result to every rectangular hole. The Navisworks bbox is only valid for sizing, never for rotation.
- **`testsData.Tests` does not exist — use `testsData.Value.TestsRoot.Children`.** Using `.Tests` directly on `DocumentClashTests` raises `AttributeError`. This applies to every script that iterates clash tests, both in Navisworks and when reading Reviewed results for coordination.
- **`ElementId.IntegerValue` removed in Revit 2024+.** Use `ElementId.Value` instead (returns a `long`). Wrap in a helper to stay compatible: `int(eid.Value)` or fall back with a try/except on `eid.IntegerValue`.

---

<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform -->
