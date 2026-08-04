# Guide: Navisworks scripts

Read this guide **before writing any Navisworks script**. It holds the host boilerplate, CastUtils casting, and the saved-script structure convention.

Related: [revit.md](revit.md) · [autocad-civil.md](autocad-civil.md) · [winforms.md](winforms.md)

---

## Standard boilerplate

Import **only the types you actually use**, explicitly. Add a `clr.AddReference` only for the
assemblies whose types appear in the script.

```python
import clr
import sys
from pathlib import Path

clr.AddReference("Autodesk.Navisworks.Api")
from Autodesk.Navisworks.Api import Application   # add other types as needed

clr.AddReference("Autodesk.Navisworks.Clash")
from Autodesk.Navisworks.Api.Clash import DocumentClash, ClashResultStatus

clr.AddReference("System.Windows.Forms")
from System.Windows.Forms import MessageBox, MessageBoxButtons, MessageBoxIcon

doc = Application.ActiveDocument
```

> Navisworks uses `Application.ActiveDocument`. This `Application` does **not** exist in Revit scripts — see [revit.md](revit.md).

> Need the COM API or `List[T]`? Add them explicitly only where used:
> `from Autodesk.Navisworks.Api.ComApi import ComApiBridge` · `from System.Collections.Generic import List`.

### ⛔ NEVER use `from <namespace> import *`

Wildcard imports on CLR namespaces (`Autodesk.Navisworks.Api`, `...Clash`, `System.Windows.Forms`, …)
are **forbidden** in this project. Always import each type by name.

Why — two concrete failure modes we hit in production:

1. **Modeless browse window.** `import *` only pulls in the types pythonnet has *already discovered*
   in its type cache. When a script runs from the **non-modal** Browse Scripts window, the cache is
   not warm, so the wildcard silently omits types → `name 'DocumentClash' is not defined` at runtime.
   The exact same script works modal and fails modeless. Explicit imports resolve on demand and always
   work.
2. **MCP sandbox.** Scripts launched through the bridge are validated more strictly; explicit imports
   keep you clear of that path too.

Explicit imports are also faster to scan, avoid name collisions (e.g. two `Application`), and make the
script's dependencies obvious. The cost is zero — `clr.AddReference` already loads the whole assembly.

---

## CastUtils — critical for type casting

pythonnet sometimes returns incorrect types, especially with interfaces (Clash API). The PyNET plugin ships a static utility `CastUtils` to correctly map objects. **Always use it when working with Clash or other interface-heavy APIs.**

```python
bundlePath = (Path.home() / "AppData" / "Roaming" / "Autodesk" / "ApplicationPlugins"
              / "RAEN.Navisworks.PyNET.bundle" / "Contents" / "2027")
sys.path.append(str(bundlePath))

clr.AddReference("Raen.Core.Pynet.Resources")
from Raen.Core.Pynet.Resources import CastUtils
```

> **Version note:** this machine has Navisworks **2027** installed — use the `2027` folder, not `2024`. If `clr.AddReference` fails, detect the real version by reading `asm.Location` via reflection instead of hardcoding.

Example — accessing clash tests (use the version-tolerant helper below, not a direct call):

```python
def ExportResults(document):
    clashDocument = CastUtils.CastTo[DocumentClash](document.Clash)
    tests = get_clash_tests(clashDocument)   # see "Clash tests — version-tolerant access"
```

Without `CastUtils`, `document.Clash` may return an unusable proxy object. This applies to any Navisworks API property that returns an interface type.

---

## Heavy models — analyze incrementally, never blind full scans

**Never send a full-property, all-descendants, all-models scan as the first move against a real
federated model.** These scripts have unknown duration (can run 10+ minutes) and the bridge/plugin
UI does not always expose a way to cancel — a hang forces the user to kill and restart the whole
application.

Before running any script that walks `model.RootItem.Descendants` across all federated models with
per-item property/category iteration:

1. **Measure scope first, with a cheap read-only query**: how many models are loaded
   (`len(list(doc.Models))`), and a rough element count per model (e.g. `sum(1 for _ in
   model.RootItem.Descendants)` on one model, or `HasGeometry` counts) — before touching properties.
2. **Go smallest-to-largest ("de menos a más")**: run the real scan on the smallest/lightest model
   first, confirm it completes and the result shape is right, then scale up to the rest — never all
   models at once on the first attempt.
3. **Bound the work**: cap values collected per property key, sample a subset of items, or restrict to
   a specific `ClassDisplayName` (e.g. only `"Tipo"` nodes) instead of every descendant — see the
   Clash Detection skill's parameter-discovery script for the pattern.
4. **If a `send_command` call times out, do not assume the script stopped — timeout does NOT mean the
   process stopped executing.** The timeout is purely on the bridge side giving up waiting for a
   response; the script keeps running inside the live Navisworks process regardless. **Do not fire any
   further command at that PID — not even `check_plugin_status`.** A plugin ping can succeed (the
   listener thread answers) while the actual script execution queue is still busy with the timed-out
   script, giving a false "it's fine" reading that leads straight into sending a second command that
   then also queues up and appears to hang. The only correct move after a timeout is to **stop and
   tell the user**, and wait for their confirmation that the operation finished (or that they killed
   and restarted Navisworks) before sending anything else to that session.
5. **Add `print()` progress statements to any script with a loop over more than a few dozen items or an
   uncertain duration — even inline scripts sent via `send_command` that will never be saved.** The
   default of keeping prints minimal during development (see §5 in `CLAUDE.md`) assumes a short script;
   it does not apply once a script might run long enough that the user needs to see it's alive in the
   Navisworks Output Window. Print every N iterations or once per logical chunk (e.g. once per clash
   test in a loop over tests), not only a final summary.

**Worked example (same session, two contrasting outcomes):** grouping ~3,700 clash results by shared
element was done right — tested on a 4-result test, then a 29-result test to measure real per-item cost
(~0.002s/item), then scaled to the 2,200-result test with a time estimate and a generous timeout.
Applying Approve/Reviewed status + comments to those same ~3,700 results (a similar-looking write loop)
was done wrong immediately after — fired at full volume (~7,400 API calls across all 11 tests) with no
prior small-scale timing test and no progress prints, using an arbitrary 180s timeout with no basis. It
genuinely was still running past that timeout (confirmed complete only once the user watched it finish
in the Navisworks UI) — the lesson isn't "it hung," it's "there was no way for either the AI or the user
to tell the difference between hung and genuinely busy," which is exactly what points 4 and 5 above fix.

This mirrors the general rule in `CLAUDE.md` §9 ("no heavy script without prior analysis and explicit
permission") — applied specifically to scans and bulk writes over federated models here.

---

## Write operations — no transactions needed

The Navisworks API does **not** use transactions for write operations via pythonnet. Call write methods directly on the document parts (`SelectionSets.Clear()`, `AppendFile()`, etc.) — no `BeginTransaction` / `Commit` wrapper required. `Document.BeginTransaction` exists in the stubs but is not needed for typical automation and does **not** work as a Python context manager (`with` raises `__enter__`).

---

## Clash tests — version-tolerant access (READ THIS before any clash script)

**The Clash API changed between Navisworks 2025 and 2026/2027.** Since every user may run a different
version, this is the single biggest source of "works on my machine" breakage in this project.

| Navisworks version | How clash tests were exposed |
|---|---|
| **2025 and earlier** | `clashTests.Tests` — a flat collection of `ClashTest` |
| **2026 / 2027** | `.Tests` **removed**. Tests live under `clashTests.Value.TestsRoot` (a folder tree). Calling `.Tests` raises `'DocumentClashTests' object has no attribute 'Tests'`. |
| **2027 (confirmed live)** | `DocumentClash` no longer exposes `.Value` directly. Full path: `clashDoc.TestsData.Value.TestsRoot`. `clashDoc.TestsData` → `DocumentClashTests`; `.Value` → `ClashTestsData`; `.TestsRoot` → iterable root node. |

### ✅ The rule — import the shared helper, never inline it

**Never call `.Tests` or `.Value.TestsRoot.Children` directly.** Import the shared, version-tolerant
helpers from `01_Scripts/00_utils/pynet_clash.py` (deployed under `…/Pynet/Library/01_Scripts/00_utils`).
One source of truth, no duplication:

```python
import sys
from pathlib import Path
sys.path.append(str(Path.home() / "AppData" / "Roaming" / "Pynet" / "Library"
                    / "01_Scripts" / "00_utils"))
from pynet_clash import get_clash_tests, iter_results

# Usage
clashDoc = CastUtils.CastTo[DocumentClash](document.Clash)
for test in get_clash_tests(clashDoc):          # version-tolerant (2025 vs 2026/2027)
    for result in iter_results(test):           # flattens ClashResultGroup items
        ...
```

`get_clash_tests` tries the old `.Tests` API and falls back to walking `Value.TestsRoot` (EAFP — *try it,
catch the failure*), so the **same script runs unchanged on any Navisworks version**. You don't need to
know *which* version removed `.Tests`; if it exists it's used, otherwise the folder-tree path runs
(recursing into `ClashTestFolder`, so tests organised in folders are still found).

> Do **not** use `getattr` / `hasattr` to probe for `.Tests` — both are **blocked by the MCP sandbox**.
> The helper uses `try / except AttributeError`, the sandbox-safe way to feature-detect a member.

> The module also exposes `iter_results(test)` — see the next section.

---

## Clash results — flatten groups when counting

`iter_results(test)` (from `pynet_clash`) handles this; the explanation: inside a test, `test.Children`
mixes individual `ClashResult` items with `ClashResultGroup` items. To count or iterate the real results,
**flatten the groups** — otherwise a
group counts as 1 (or is skipped entirely on a `CastTo[ClashResult]`, which returns `None` for a group):

```python
def iter_results(test):
    for child in test.Children:
        if child.IsGroup:
            for r in child.Children:   # enter the group
                yield r
        else:
            yield child
```

Combine both helpers in a clash script: `for test in get_clash_tests(clashDoc): for r in iter_results(test): ...`

---

## Key API patterns (this project)

- **Tolerances are in feet** when configuring clash tests.
- Create **SearchSets before clash tests** so the tests stay dynamic.
- See `01_Scripts/01_Navisworks/` for validated examples by use case:
  - `01_ModelManagement/` — open, append, list, publish NWD
  - `02_SearchSets/` — Search Sets from property conditions
  - `03_ClashDetection/` — export, import, rename, run clash tests
  - `04_DataAnalysis/` / `08_DataAnalysis/` — chart & dashboard generation
  - `05_QueryElements/` — isolate, query custom category values, measurements
  - `07_IFCExport/` — NWC/NWD → IFC export pipeline

---

## Code structure convention (saved scripts)

When **saving** a script (to source or deploying to a button), use the full class-based structure with a single entry-point call at the bottom, and add informative `print` statements (progress, summary, results). The user runs it without the AI in the loop.

```python
class FeatureManager:
    @staticmethod
    def Run(document):
        data = DataProcessor.Process(document)
        print(f"Processed {len(data)} elements")
        DialogManager.ShowResult(data)

class DataProcessor:
    @staticmethod
    def Process(document):
        print("Processing...")
        return result

class DialogManager:
    @staticmethod
    def ShowResult(data):
        MessageBox.Show(str(data), "PyNet", MessageBoxButtons.OK, MessageBoxIcon.Information)

# Entry point
FeatureManager.Run(doc)
```
