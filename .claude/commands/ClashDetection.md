# Skill: ClashDetection

Start the conversation in english. If the user request to change you can use the user language.
Full Clash Detection workflow for the PyNET platform on Autodesk Navisworks.

> **Related skill:** [ClashCoordination.md](ClashCoordination.md) — reads Reviewed results from this workflow and creates the corresponding floor openings in Revit. If that skill is active, read this file too for full Navisworks API context.

## Context

- Classification parameter: `PYNET_Classification` — a **type parameter** that appears at multiple hierarchy levels
- Navisworks API uses **feet** internally for tolerances → always convert with `mm / 1000 / 0.3048`
- Clash tests must reference **dynamic SearchSets**, never static snapshots via `CopyFrom(FindAll(...))`

### PYNET_Classification — hierarchy and category

`PYNET_Classification` is a Revit type parameter. In a Navisworks NWC it appears in **three** places:

| Where | Internal category | Display name | hasGeometry |
|---|---|---|:---:|
| TYPE container node (class=Tipo) | `lcldrevit_tab_type` | `"Tipo"` | False |
| Instance node (class=element) | `LcRevitData_Type` | `"Tipo de Revit"` | False |
| Instance node (shared param export) | `LcRevitData_TypeCustom` | `"Tipo Personalizar"` | False |

**SearchSets must target the TYPE container (`lcldrevit_tab_type / "Tipo"`)**, because:
- The TYPE container groups all instances of that type as its children
- Clash detection traverses children → finds actual geometry
- Targeting `LcRevitData_Type` on instance nodes does NOT work (instances have `hasGeo=False` and the search engine doesn't resolve their geometry children)

The discovery script must look for `lcldrevit_tab_type` as the primary candidate, with `LcRevitData_TypeCustom` as fallback for correctly-shared-parameter exports.

## Workflow

### 1. Verify active session
Use `list_active_instances` to get the active PID.

### 2. Discover and validate the classification parameter

**Every federated model is different. Never assume a fixed parameter name or property category — always discover first.**

#### Step 2a — Discovery: find the classification parameter

Ask the user: *"Which parameter is used to classify elements in this project?"*

If the user doesn't know or wants you to detect it automatically, run a discovery scan.

> ⚠ **Performance — mandatory, this caused a real production incident (session hang, forced Navisworks
> restart, twice in the same afternoon).** Never run this scan over `model.RootItem.Descendants`
> unfiltered — that walks every geometry/instance node (thousands to tens of thousands per model) and
> reads every property on every one of them, each read a pythonnet↔.NET interop call. A property
> like the classification parameter lives on the **TYPE container node** (`ClassDisplayName == "Tipo"`)
> and Navisworks re-exposes the *same* value on every instance under it — scanning unfiltered means
> reading and hashing the identical value hundreds of times per type instead of once.
>
> **Always filter to container nodes first**: `if item.ClassDisplayName != "Tipo": continue` before
> touching `PropertyCategories`. Measured on the real Snowdon Towers sample: unfiltered scan over one
> mid-size model (9,710 descendants) hung past 120s and never returned; the same discovery filtered to
> `"Tipo"` nodes only (131 nodes) completed in **~1 second**. Scale is not the bottleneck — the number
> of interop calls is. Follow the general rule in `docs/navisworks.md` §"Heavy models — analyze
> incrementally": measure scope first, smallest model first, bounded work.

```python
from collections import Counter, defaultdict

# (cat_internal, cat_display, prop_display) → set of unique values found
param_index = defaultdict(set)

for model in doc.Models:
    for item in model.RootItem.Descendants:
        if item.ClassDisplayName != "Tipo":   # container nodes only — see perf note above
            continue
        for cat in item.PropertyCategories:
            for prop in cat.Properties:
                try:
                    val = prop.Value.ToDisplayString()
                    if val:
                        param_index[(cat.Name, cat.DisplayName, prop.DisplayName)].add(val)
                except:
                    pass

# Score candidates: prefer short distinct values (codes), high element count, present in multiple models
results = []
for (cat_int, cat_disp, prop_disp), values in param_index.items():
    avg_len = sum(len(v) for v in values) / len(values) if values else 0
    score = len(values) if avg_len <= 20 else 0  # short values = likely codes
    results.append({
        "category_internal": cat_int,
        "category_display": cat_disp,
        "property": prop_disp,
        "unique_values": sorted(list(values))[:20],
        "unique_value_count": len(values),
        "score": score
    })

results.sort(key=lambda x: -x["score"])
ia_Result = results[:20]
```

After running the scan, **analyze the results and propose the best candidate(s)** before asking the user to confirm:

- **Best candidate criteria:** short unique values (2–10 chars), moderate count of distinct values (3–20), present across all models, property name suggests classification (contains words like "classification", "type", "code", "clase", "tipo").
- **Present a ranked shortlist** (top 3–5), explain why each is a good or poor candidate, and state your recommendation clearly.
- Then ask: *"Is this the parameter you want to use, or do you prefer another one from the list?"*

**Do not proceed to 2b until the user has confirmed the parameter name and its property category.**

Once confirmed, store:
- `PARAM_DISPLAY_NAME` — the display name of the property (e.g. `"PYNET_Classification"`)
- `PARAM_CAT_INTERNAL` — the internal category name where it lives (e.g. `"LcRevitData_Type"`)
- `PARAM_CAT_DISPLAY` — the display name of that category (e.g. `"Tipo de Revit"`) — needed for SearchSet conditions

#### Step 2a-fallback — no classification parameter found (test/sample models)

Some models (generic Autodesk samples, test federations without a project-specific export) carry no
custom classification parameter at all — the discovery scan above returns only dimensional/geometry
properties (width, area, nominal weight...), never short codes. **Do not silently pick a fallback basis
— ask the user.** Present the options and let them decide:

- **By native Revit Category** — container node level `ClassDisplayName == "Categoría"` (one level
  above `"Tipo"`, even fewer nodes, cheap to scan — confirmed ~1s across 5 federated models on the
  Snowdon Towers sample):
  ```python
  for item in model.RootItem.Descendants:
      if item.ClassDisplayName == "Categoría":
          category_counts[item.DisplayName] += 1
  ```
  Each category name found (e.g. "Muros", "Pilares estructurales", "Tuberías", "Conductos") becomes a
  code; SearchSets/tests follow the same process as steps 4–9 using the container node's `DisplayName`
  directly (no property lookup needed — the container node name IS the code).
- **By discipline/source model** — one code per federated NWC (Architectural, Structural, Electrical...).
  Coarser, useful for a quick first pass but hides intra-discipline conflicts (e.g. wall vs slab in the
  same Architectural model).
- **Any other property the user names** — treat it like a confirmed parameter from step 2a and skip to 2b.

Whichever basis is chosen, confirm exclusions with the user explicitly per case (e.g. rebar/reinforcement
categories — embedded in concrete, typically no coordination value — ask before including or excluding,
do not assume).

#### Step 2b — Validation: parameter populated and coverage

Once the parameter is confirmed, validate each model. The analysis works at **TYPE node level** — that is the unit that SearchSets target, so that is the unit where gaps matter.

**Implementation notes (learned from real models):**
- Filter by `item.ClassDisplayName == "Tipo"` to target only TYPE container nodes — do not scan all descendants blindly.
- Use `hash(item)` (not `id(item)`) to track .NET objects. Python.NET creates a new wrapper each time `.Parent` is accessed, so `id()` is not stable across calls.
- Count geometry **downward** from classified TYPE nodes (`.Descendants`) — do not walk upward from geometry elements via `.Parent`. Downward traversal is reliable; upward is not.
- Use a `covered_geo_hashes` set to avoid double-counting geometry elements that appear under multiple TYPE nodes.

```python
from collections import defaultdict

# PARAM_DISPLAY_NAME and PARAM_CAT_INTERNAL confirmed by user in step 2a
PARAM_DISPLAY_NAME = "..."   # fill from discovery
PARAM_CAT_INTERNAL = "..."   # fill from discovery

results = []
for model in doc.Models:
    model_name = model.FileName.split("\\")[-1]

    # Pass 1: scan TYPE nodes only — classify them
    classified_types = {}    # hash(item) → code
    unclassified_types = []  # names of TYPE nodes missing the param

    for item in model.RootItem.Descendants:
        if item.ClassDisplayName != "Tipo":
            continue
        code = None
        for cat in item.PropertyCategories:
            if cat.Name != PARAM_CAT_INTERNAL:
                continue
            for prop in cat.Properties:
                if prop.DisplayName != PARAM_DISPLAY_NAME:
                    continue
                try:
                    val = prop.Value.ToDisplayString()
                    if val:
                        code = val
                except:
                    pass
        if code:
            classified_types[hash(item)] = code
        else:
            if len(unclassified_types) < 15:
                unclassified_types.append(item.DisplayName or "(sin nombre)")

    # Pass 2: count geometry under each classified TYPE node (downward traversal)
    code_counts = defaultdict(int)
    covered_geo_hashes = set()

    for item in model.RootItem.Descendants:
        if item.ClassDisplayName != "Tipo":
            continue
        h = hash(item)
        if h not in classified_types:
            continue
        code = classified_types[h]
        for desc in item.Descendants:
            if desc.HasGeometry:
                dh = hash(desc)
                if dh not in covered_geo_hashes:
                    covered_geo_hashes.add(dh)
                    code_counts[code] += 1

    total_geo = sum(1 for it in model.RootItem.Descendants if it.HasGeometry)
    classified_geo = sum(code_counts.values())
    unclassified_geo = total_geo - classified_geo
    coverage_pct = round(classified_geo / total_geo * 100, 1) if total_geo > 0 else 0.0
    total_types = len(classified_types) + len(unclassified_types)

    results.append({
        "model": model_name,
        "total_type_nodes": total_types,
        "classified_types": len(classified_types),
        "unclassified_type_count": len(unclassified_types),
        "unclassified_type_names": unclassified_types,
        "total_geometry_elements": total_geo,
        "classified_geo": classified_geo,
        "unclassified_geo": unclassified_geo,
        "coverage_pct": coverage_pct,
        "elements_per_code": dict(sorted(code_counts.items()))
    })

ia_Result = results
```

**Always present the coverage report before proceeding — at TYPE node level, not just geometry %:**

| Model | Type nodes | Classified | Unclassified types | Geo coverage |
|-------|:----------:|:----------:|:------------------:|:------------:|
| ModeloR_ARQ.nwc | 5 | 3 | 2 | 66.7 % |
| ModeloR_EST.nwc | 3 | 2 | 1 | 64.7 % |

**How to interpret unclassified TYPE nodes — always investigate before flagging:**

Not every unclassified TYPE node is a real problem. Look at the names and decide:
- **Reference/auxiliary elements** (level markers, axes, grids, construction planes) — legitimate, they should not be classified. Do not flag these as errors.
- **Real buildable elements** (walls, columns, slabs, pipes, ducts) — these ARE a gap. Any geometry under them will be invisible to clash tests. Report these clearly and ask the user to decide.

Present the distinction explicitly:

```
Unclassified TYPE nodes:
  ✓ "Extremo inicial 8 mm" — level marker (reference element, expected)
  ✗ "Interior - bloques 140 mm" — wall type missing classification (real gap)
```

Only block on real buildable gaps — reference elements do not require user action.

#### ⚠ Category consistency check

Compare the internal category name where the parameter was found across models. If models differ, SearchSet conditions will need to be built per-model — flag this and ask the user to confirm before continuing.

### 3. Discover model classifications
Already obtained from step 2b. Build a map: `{code: (cat_internal, cat_display)}` using each model's actual category, to be used when creating SearchSets.

### 4. Create SearchSets (one per code)

**Before creating SearchSets, determine the correct category for the condition.** The category that works for the Search API is NOT necessarily the same as where you found the parameter in step 2. Test all candidate categories first and use the one that returns the highest element count.

```python
# Test which category display name returns results via the Search API
test_cats = ["Tipo", "Tipo de Revit", "Tipo Personalizar"]  # adapt to project
for cat_display in test_cats:
    search = Search()
    search.Locations = SearchLocations.DescendantsAndSelf
    search.Selection.SelectAll()
    cond = SearchCondition.HasPropertyByDisplayName(cat_display, PARAM_DISPLAY_NAME).EqualValue(
        VariantData.FromDisplayString(some_known_code)
    )
    cond_list = List[SearchCondition]()
    cond_list.Add(cond)
    search.SearchConditions.AddGroup(cond_list)
    count = sum(1 for _ in search.FindAll(doc, False))
    print(f"{cat_display}: {count} items")
# → pick the category with the highest count
```

> **Learned from real models:** `lcldrevit_tab_type` ("Tipo") only returns 1 item per code (the TYPE container node itself, no geometry visible). `LcRevitData_Type` ("Tipo de Revit") returns the instance nodes (direct parents of geometry) and produces a working selection. Always test before committing.

Once the correct category is confirmed, create and **always verify** each SearchSet before saving:

```python
CAT_DISPLAY = "..."   # confirmed by test above
CODES = [...]         # discovered in step 2

results = []
for code in CODES:
    search = Search()
    search.Locations = SearchLocations.DescendantsAndSelf
    search.Selection.SelectAll()
    cond = SearchCondition.HasPropertyByDisplayName(CAT_DISPLAY, PARAM_DISPLAY_NAME).EqualValue(
        VariantData.FromDisplayString(code)
    )
    cond_list = List[SearchCondition]()
    cond_list.Add(cond)
    search.SearchConditions.AddGroup(cond_list)

    # Verify before saving — never create an empty SearchSet
    count = sum(1 for _ in search.FindAll(doc, False))
    if count == 0:
        results.append({"code": code, "status": "EMPTY — not created", "items": 0})
        continue

    ss = SelectionSet(search)
    ss.DisplayName = code
    doc.SelectionSets.AddCopy(ss)
    results.append({"code": code, "status": "OK", "items": count})

ia_Result = results
```

Report the verification table to the user before proceeding:

| Code | Items in set | Status |
|------|:------------:|:------:|
| CON | 2 | OK |
| PIL | 9 | OK |
| … | … | … |

If any set is EMPTY, investigate why before continuing — a missing set means that discipline will be invisible in all clash tests.

### 5. Propose the theoretical matrix — MANDATORY USER CONFIRMATION

**Always send the full matrix to the user and wait for explicit confirmation before creating any clash test. Never skip this step.**

Present **two complementary tables**:

#### Table 1 — Triangular clash matrix (single unified grid)

All codes on both axes. Upper triangle only (each pair appears once). Cells:
- **A** = 10 mm tolerance (MEP vs any element)
- **B** = 25 mm tolerance (PIL vs ARQ)
- **C** = 50 mm tolerance (LOS vs ARQ)
- **—** = same model, no test
- *(empty)* = symmetric, already covered above the diagonal

Example with codes CON, TUB, LOS, PIL, FAC, MUR, PAR:

|  | **FAC** | **MUR** | **PAR** | **LOS** | **PIL** | **CON** | **TUB** |
|--|:-------:|:-------:|:-------:|:-------:|:-------:|:-------:|:-------:|
| **FAC** | — | — | — | C | B | A | A |
| **MUR** | | — | — | C | B | A | A |
| **PAR** | | | — | C | B | A | A |
| **LOS** | | | | — | — | A | A |
| **PIL** | | | | | — | A | A |
| **CON** | | | | | | — | — |
| **TUB** | | | | | | | — |

**A** = 10 mm · **B** = 25 mm · **C** = 50 mm · **—** = mismo modelo

#### Table 2 — Test list with detail

| Test | Selection A | Selection B | Tolerance |
|------|-------------|-------------|:---------:|
| CON vs LOS | CON | LOS | 10 mm |
| TUB vs LOS | TUB | LOS | 10 mm |
| … | … | … | … |

Rule: **never create intra-model tests** (elements from the same NWC file do not clash against each other).

Only proceed to step 6 after the user explicitly confirms the proposed matrix (or requests changes).

### 6. Create ClashTests referencing SearchSets

```python
def find_set(root, name):
    for item in root.Children:
        if item.DisplayName == name:
            return item
        if item.IsGroup:
            found = find_set(item, name)
            if found:
                return found
    return None

# Get SelectionSource from the set
item = find_set(doc.SelectionSets.RootItem, code)
source = doc.SelectionSets.CreateSelectionSource(item)

# Create test
clashDoc = CastUtils.CastTo[DocumentClash](doc.Clash)
testsData = clashDoc.TestsData

test = ClashTest()
test.DisplayName = "CON vs MUR"
test.TestType = ClashTestType.Hard
test.Tolerance = mm_to_ft(10)
test.SelectionA.Selection.SelectionSources.Add(source_a)
test.SelectionB.Selection.SelectionSources.Add(source_b)
testsData.TestsAddCopy(None, test)  # None = root level
```

### 7. Apply tolerances

Standard project criteria — adjust based on user confirmation:

| Interface | Tolerance |
|-----------|:---------:|
| LOS vs ARQ (MUR/FAC/PAR) | 50 mm |
| PIL vs ARQ (MUR/FAC/PAR) | 25 mm |
| MEP vs any element | 10 mm |

To update an existing test:

```python
new_test = ClashTest()
new_test.DisplayName = live_test.DisplayName
new_test.TestType = live_test.TestType
new_test.Tolerance = mm_to_ft(50)
new_test.SelectionA.CopyFrom(live_test.SelectionA)
new_test.SelectionB.CopyFrom(live_test.SelectionB)
testsData.TestsEditTestFromCopy(live_test, new_test)
```

### 8. Run the tests

```python
testsData.TestsRunAllTests()
```

### 9. Report results

Iterate `testsData.Value.TestsRoot.Children` and count `sum(1 for _ in test.Children)` per test.

### 10. Preliminary analysis — propose Approve / Reviewed

Extract element info for every clash result (name, category, PYNET code, diameter, 3D center) and apply the approval criteria from the **Clash Approval Criteria** section below.

Present a table to the user:

| # | Test | Depth | Element A | Ø | Element B | Proposal | Reason |
|---|------|:---:|---|:---:|---|:---:|---|

Ask the user to confirm or adjust before applying anything.

### 11. Visual analysis of doubtful clashes

After presenting the preliminary analysis, if there are any **Reviewed** clashes (or cases where the automatic criteria could not reach a confident decision), ask:

> "I have **X** clashes flagged as Reviewed. Do you want me to generate and analyze an image for each one before applying the statuses?"

If the user confirms:
1. Generate images using `TestsImageForResult` (see **Clash Review & Approval workflow** section) and save to the standard folder.
2. Read each image with the Read tool and provide a brief visual description of what the conflict looks like.
3. Revise the proposal if the visual analysis reveals something the data alone did not capture.
4. Present the final updated table and ask for confirmation before writing any status to the model.

### 12. Apply statuses and comments, then group

Only after the user confirms the final proposal:

1. **Apply status** with `TestsEditResultStatus`.
2. **Add comment** with `TestsEditResultComments` — takes `CommentCollection`, not a plain string. `Comment`, `CommentCollection` and `CommentStatus` are in `Autodesk.Navisworks.Api`, **not** in the Clash namespace:
   ```python
   from Autodesk.Navisworks.Api import Comment, CommentCollection, CommentStatus

   body = f"[Auto-review {run_date}] {reason}"
   comments = CommentCollection()
   comments.Add(Comment(body, CommentStatus.New))
   testsData.TestsEditResultComments(result, comments)
   ```
3. **Group related clashes** — after all statuses are applied, call `ClashGrouper.GroupBySharedElement` per test (see **Grouping clash results** section below).

> Always apply statuses first, then group. Grouping runs last because it moves results into sub-groups which changes the iteration structure.

> ⚠ **Performance — this is a write-heavy loop over every result, not a quick read.** Applying status +
> comment to thousands of results means two API calls each (`TestsEditResultStatus` +
> `TestsEditResultComments`) — real, possibly slow work, not something to fire once at full volume with
> an arbitrary timeout. Before running this over the full result set:
> - Add a `print()` every test (or every N results) so progress is visible in the Output Window while it
>   runs — see `docs/navisworks.md` "Heavy models" section, point 5.
> - If the result count is large (thousands), consider timing a small test first to set a realistic
>   timeout, the same way step "Grouping clash results" above tests small→medium→large.
> - A `send_command` timeout here does **not** mean the write loop stopped — it is very likely still
>   running inside Navisworks. Do not send another command to the same session; stop and tell the user,
>   then wait for confirmation it finished (verify afterwards by reading back a sample of `result.Status`
>   values, cheap and fast) rather than assuming success or failure.

### 13. Generate HTML dashboard

After applying statuses and groups, generate a summary HTML report and open it in the browser with `webbrowser.open()`.

**Navisworks status colors — always use these, no exceptions:**

| Status | Color |
|--------|-------|
| New | `#ef4444` (red) |
| Active | `#f97316` (orange) |
| Reviewed | `#3b82f6` (blue) |
| Approved | `#22c55e` (green) |
| Resolved | `#eab308` (yellow) |

**Dashboard must include:**
- KPI row: total clashes + one KPI per status present + number of federated models
- **Donut chart** — global status distribution
- **Stacked horizontal bar** — clashes per test, colored by status
- **Grouped bar** — clashes per discipline code, colored by status
- **Models table + bar** — model file names and geometry element count
- **Detail table** — all clashes with test, group, status badge, and reason (strip the `[Auto-review YYYY-MM-DD]` prefix for readability)

**Output path:**
```
Path.home() / "AppData" / "Roaming" / "Pynet" / "Navisworks" / f"ClashReport_{doc_name}_{YYYYMMDD_HHMMSS}.html"
```

**Key implementation notes:**
- Use `plotly.graph_objects` + `plotly.offline.plot(output_type="div")` for charts; embed `pyo.get_plotlyjs()` inline so the file is self-contained with no internet dependency.
- Iterate `test.Children` — handle both grouped (`child.IsGroup`) and flat results.
- KPI border-top color matches the status color for visual consistency.
- Open with `webbrowser.open(str(html_path))` at the end of the script.

---

## Utilities

```python
import math

def mm_to_ft(mm):
    return mm / 1000 / 0.3048

# CastUtils — always required for DocumentClash
# Bundle path: find the folder that actually contains the DLL (2024, 2025, 2026 or 2027)
bundle_base = Path.home() / "AppData" / "Roaming" / "Autodesk" / "ApplicationPlugins" / "Raen.Navisworks.Pynet.bundle" / "Contents"
bundlePath = next((d for d in bundle_base.iterdir() if d.is_dir() and (d / "Raen.Core.Pynet.Resources.dll").exists()), None)
if bundlePath is None:
    raise RuntimeError("PyNET bundle not found. Check Navisworks installation.")
sys.path.append(str(bundlePath))
clr.AddReference("Raen.Core.Pynet.Resources")
from Raen.Core.Pynet.Resources import CastUtils

# Clash namespace requires explicit AddReference
clr.AddReference("Autodesk.Navisworks.Clash")
from Autodesk.Navisworks.Api.Clash import *

clashDoc = CastUtils.CastTo[DocumentClash](doc.Clash)
testsData = clashDoc.TestsData
```

## Clash Review & Approval workflow

### Generating and analyzing clash images

Each clash result has a built-in viewpoint. Use `TestsImageForResult` to render it directly — no screen capture needed.

**Standard output folder:**

```
C:\Users\{user}\AppData\Roaming\Pynet\Navisworks\{YYYYMMDD}_{federated_name}\
```

```python
from datetime import datetime

clr.AddReference("System.Drawing")
from System.Drawing import Bitmap

date_str = datetime.now().strftime("%Y%m%d")
doc_name = Path(doc.FileName).stem if doc.FileName else "Unknown"
save_dir = Path.home() / "AppData" / "Roaming" / "Pynet" / "Navisworks" / f"{date_str}_{doc_name}"
save_dir.mkdir(parents=True, exist_ok=True)
```

```python
# ImageGenerationStyle values: Scene, ScenePlusOverlay, SceneUsingRayTrace
# ScenePlusOverlay includes the clash highlight (red overlay on conflicting elements)
bmp = testsData.TestsImageForResult(result, ImageGenerationStyle.ScenePlusOverlay, 800, 600)
img_path = save_dir / f"clash_{idx:02d}_{test_name.replace(' ', '_')}.png"
bmp.Save(str(img_path))
```

**Typical workflow for Reviewed clashes:**

```python
from datetime import datetime

date_str = datetime.now().strftime("%Y%m%d")
doc_name = Path(doc.FileName).stem if doc.FileName else "Unknown"
save_dir = Path.home() / "AppData" / "Roaming" / "Pynet" / "Navisworks" / f"{date_str}_{doc_name}"
save_dir.mkdir(parents=True, exist_ok=True)

clash_index = 1
for test in testsData.Value.TestsRoot.Children:
    for r in test.Children:
        if str(r.Status) == "Reviewed":
            bmp = testsData.TestsImageForResult(r, ImageGenerationStyle.ScenePlusOverlay, 800, 600)
            img_path = save_dir / f"clash_{clash_index:02d}_{test.DisplayName.replace(' ', '_')}.png"
            bmp.Save(str(img_path))
        clash_index += 1
```

After saving, read each image with the Read tool and analyze visually. The overlay colors:
- **Green** = one of the clashing elements (Selection A or B)
- **Red** = the penetration zone / conflicting geometry

> **Note:** `TestsViewpointForResult(result)` returns the `Viewpoint` object without rendering — use `TestsImageForResult` for actual image generation.

---

### Changing clash result status

```python
# Assignee is in Autodesk.Navisworks.Api (NOT in Autodesk.Navisworks.Api.Clash)
from Autodesk.Navisworks.Api import Assignee  # explicit import required — not included in wildcard from Clash

assignee = Assignee()
assignee.DisplayName = "PyNET"  # or any reviewer name

testsData.TestsEditResultStatus(result, ClashResultStatus.Approved, assignee)
testsData.TestsEditResultStatus(result, ClashResultStatus.Reviewed, assignee)
```

Available `ClashResultStatus` values: `New`, `Active`, `Reviewed`, `Approved`, `Resolved`

**Iteration pattern** — always iterate consistently to keep index mapping stable. Use a helper that handles results inside groups:

```python
def iter_all_results(test):
    """Yield all ClashResult items under a test, including those inside groups."""
    for child in test.Children:
        if child.IsGroup:
            for r in child.Children:
                yield r
        else:
            yield child

clash_index = 1
for test in testsData.Value.TestsRoot.Children:
    for result in iter_all_results(test):
        # process clash_index
        clash_index += 1
```

**Additional metadata methods** (all require the `result` object, not the test):

```python
testsData.TestsEditResultApprovedBy(result, assignee, ...)  # set approver
testsData.TestsEditResultAssignedTo(result, assignee, ...)  # assign to reviewer
# Comments — takes CommentCollection, NOT a plain string
comments = CommentCollection()
comments.Add(Comment("text", CommentStatus.New))
testsData.TestsEditResultComments(result, comments)
# TestsEditResultDescription takes IClashResult + plain string
iresult = CastUtils.CastTo[IClashResult](result)
testsData.TestsEditResultDescription(iresult, "text")
```

> **Note on `Assignee`:** constructing `Assignee()` directly works in pythonnet. `DisplayName` is a settable string property. Passing `None` for the `who` argument raises `ArgumentNullException`.

---

### Grouping clash results

When multiple clash results involve the **same element** (e.g. one facade panel clashing with 3 separate columns), group them inside a `ClashResultGroup` so the Navisworks UI shows them as a single logical issue.

**Grouping criterion:** within a test, if any element (Item1 or Item2) appears in 2 or more clash results → group those results together under that element's name.

> ⚠ **Performance — do not re-scan `test.Children` before every move.** An earlier version of this
> pattern re-found `current_idx` with a fresh `for j, child in enumerate(test.Children)` scan before
> every single `TestsMove` call — that's O(n) per move × n moves = **O(n²)** in the number of flat
> results. On a real 2,200-result test this pattern would mean millions of live .NET child-collection
> reads. Track the index **locally in Python** instead (a plain list mirroring the flat children's
> order, updated in place after each move) — this drops the cost to O(n) total. Confirmed on a real
> 2,200-result / 540-group case: **17s** with the local-index version vs. an unmeasured, likely
> multi-minute runtime with the naive re-scan version. **Test on a small test (a few results) then a
> medium one (~30) to confirm correctness and measure real per-item cost before running on the largest
> test** — do not go straight to the biggest test first.

**API pattern — confirmed working, O(n) version:**

```python
from collections import defaultdict

def group_by_shared_element(testsData, test):
    children = list(test.Children)
    flat = [(hash(r), r) for r in children if not r.IsGroup]
    if len(flat) < 2:
        return

    # Local index mirroring the live flat-children order — avoids re-scanning
    # test.Children (a .NET collection) before every move. New groups are
    # appended at the end by TestsAddCopy, so they never shift these indices.
    order = [rh for rh, r in flat]
    pos = {rh: i for i, rh in enumerate(order)}

    elem_map = defaultdict(list)
    for rh, r in flat:
        try:
            elem_map[hash(r.Item1)].append((rh, r.Item1.DisplayName))
            elem_map[hash(r.Item2)].append((rh, r.Item2.DisplayName))
        except:
            pass

    processed = set()
    for elem_hash, entries in elem_map.items():
        entries = [e for e in entries if e[0] not in processed]
        if len(entries) < 2:
            continue

        elem_name = entries[0][1]
        group_name = f"{elem_name} – {len(entries)} clashes"

        group = ClashResultGroup()
        group.DisplayName = group_name
        testsData.TestsAddCopy(test, group)  # adds a copy — must re-find the live reference

        live_group = None
        for child in test.Children:
            if child.IsGroup and child.DisplayName == group_name:
                live_group = child
                break
        if live_group is None:
            continue

        for move_idx, (rh, _name) in enumerate(entries):
            current_idx = pos.get(rh)   # O(1) local lookup, no .NET scan
            if current_idx is None:
                continue
            testsData.TestsMove(test, current_idx, live_group, move_idx)
            processed.add(rh)
            # keep the local index in sync: remove this entry, shift the rest down by 1
            del order[current_idx]
            for h in order[current_idx:]:
                pos[h] -= 1
            del pos[rh]
```

**Key points:**
- `TestsAddCopy(parent, item)` — adds a copy; the returned object is not the live reference. Always search `test.Children` by `DisplayName` to get the actual live group.
- `TestsMove(oldParent, oldIndex, newParent, newIndex)` — moves by index. Track that index locally in Python (see perf note above) rather than re-scanning the live collection before every call.
- Run grouping **after** applying all statuses and comments — moving results into groups changes the iteration structure.
- Use `hash()` (not `id()`) to track .NET objects across calls — `hash()` maps to `GetHashCode()` and is stable.

## Clash Approval Criteria

Project rules for deciding whether a clash can be **Approved** (false positive / accepted condition) vs flagged as **Reviewed** (real issue requiring coordination).

> These rules are definitive. Apply them mechanically — no judgment calls unless the geometry is ambiguous.

---

### RULE 1 — MEP vs structural elements (PIL / beams): always Reviewed, 100%

**Any clash between an MEP element (TUB or CON) and a structural element (column or beam) is ALWAYS Reviewed. No exceptions.**

- Diameter does not matter.
- Penetration depth does not matter.
- Proximity to other elements does not matter.

**Structural PYNET codes:** `PIL` (columns) and any beam codes present in the project.

**Why:** Structural elements carry loads. Any opening requires explicit sign-off from the structural engineer. There is no safe threshold.

---

### RULE 2 — Pipes through slabs (TUB vs LOS): Approve when conditions met

A pipe clashing with a slab or floor (`LOS`) can be **Approved** when ALL of the following are true:

1. **Pipe diameter < 175 mm** — a standard sleeve (pasatubos) can resolve it without structural coordination.
2. **No nearby MEP interference within ~1000 mm** — no other clash (CON or TUB) at the same location that would require a combined, larger structural opening.

If either condition fails → **Reviewed**.

**How to extract diameter:** read the pipe's `LcRevitData_Element` (display: `"Componente"`) property `"Diámetro"` (exact string with accent). Also available: `"Diámetro exterior"`, `"Diámetro interno"`.

**How to check spatial proximity:** compare `result.Center` (in feet → convert ×304.8 to mm) between the TUB clash and all other MEP clashes. Use 3D Euclidean distance with `math.sqrt`. Flag as Reviewed if any other MEP clash is within 1000 mm.

```python
import math
dist = math.sqrt((cx1 - cx2)**2 + (cy1 - cy2)**2 + (cz1 - cz2)**2)  # mm
```

> **Critical:** "no nearby interference" means no other clash physically close in 3D space — NOT just "no other clash in the same test". A TUB vs LOS 570 mm from a CON vs LOS means both go through the same slab zone → the opening must account for both → Reviewed.

---

### RULE 3 — Ducts through slabs (CON vs LOS): always Reviewed

Ducts require a larger opening that must be coordinated with the structural model. Always **Reviewed**, regardless of duct size or penetration depth.

---

### RULE 4 — Structural columns embedded in facade (PIL vs FAC): always Approved

Perimeter columns partially overlapping the facade skin are **always Approved** — intentional architectural/structural condition, not a coordination issue.

---

### RULE 5 — Columns wider than partition (PIL vs PAR): always Reviewed

When a column is wider than the partition it crosses, the architectural/structural conflict must be resolved explicitly. Always **Reviewed**.

---

### Summary table

| Clash | Condition | Decision |
|-------|-----------|:--------:|
| TUB/CON vs PIL or beam | any | **Reviewed** |
| TUB vs LOS | Ø < 175 mm AND no nearby MEP within 1000 mm | **Approve** |
| TUB vs LOS | Ø ≥ 175 mm OR nearby MEP within 1000 mm | **Reviewed** |
| CON vs LOS | any | **Reviewed** |
| PIL vs FAC | perimeter column overlapping facade | **Approve** |
| PIL vs PAR | column wider than partition | **Reviewed** |

> **Tie-break rule:** When in doubt — always **Reviewed**. The cost of missing a real issue is always higher than the cost of flagging a false positive.

---

## Common API pitfalls

- **`testsData.Tests` does not exist.** The correct path to iterate clash tests is always `testsData.Value.TestsRoot.Children`. Using `.Tests` directly on `DocumentClashTests` raises `AttributeError` at runtime.

---

<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform -->
