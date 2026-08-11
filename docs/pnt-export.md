<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform -->

# Guide: exporting a `.pnt` for the PyNET VS Code viewer

How to generate a `.pnt` package that the PyNET viewer (ThatOpen / web-ifc fragments, embedded in
the VS Code extension) loads and renders. Written while building the fire-risk digital-twin `.pnt`
(see the `PowerlineFireRisk` / `WindSiting` skills and `04_QGIS`).

Canonical reference producer: `01_Scripts/01_Navisworks/07_IFCExport/NavisworksPNT_IFC_Fast.py`
(the Navisworks → IFC → `.pnt` exporter). Copy its conventions — they are known to render.

---

## What a `.pnt` is

A plain **ZIP** archive containing:

```
<name>.pnt
├── clashes.json          # manifest the dashboard/viewer reads first
├── manifest.json         # optional (version/format metadata; not required to render)
├── properties.json       # optional (pnt_id → element properties, for the Properties panel)
└── models/
    └── <model>.ifc        # one or more IFC4 files (the geometry)
```

The `classification` array's `basis` field states which parameter was actually measured —
`"PYNET_Classification"`, or `"Categoría (fallback — PYNET_Classification no encontrado)"` when the
project doesn't carry that type parameter (e.g. generic/sample models). `ClassificationAnalyzer`
(`NavisworksPNT_IFC_Fast.py`) tries PYNET_Classification first and only falls back to native Revit
Category if it finds zero classified types across the whole federation — this avoids a misleading
"0% coverage" being reported for a parameter the project never used in the first place.

`clashes.json` is the entry point (`03_Viewer/server/pnt_server.py` extracts the zip and reads it).
Minimum shape to render geometry — **clashes are optional, an empty list is fine**:

```json
{
  "project": "Gemelo riesgo incendio - La Muela",
  "models": [{ "fileName": "riesgo.ifc", "name": "Riesgo incendio" }],
  "clashes": [],
  "classification": []
}
```

The dashboard builds the viewer URL from `models[].fileName` (`?models=riesgo.ifc,...`); the viewer
fetches each from `/models/<fileName>`. The server's `/models/<fn>` route checks the extract root
first, then `models/` — so putting the IFC under `models/` works. `properties.json` is served from
`/data/properties.json` (the viewer fetches it; missing is non-fatal).

## How the viewer loads it

- Open via the MCP bridge tool `viewer_load_package(<path.pnt>)`, then `viewer_fit`. `viewer_status`
  reports the running viewer (port, package, dataDir).
- The viewer auto-loads the models listed in `clashes.json` (`config.autoLoad`, `config.modelUrls`).
- Models are **IFC** parsed by ThatOpen `IfcLoader` (web-ifc) into fragments — NOT glTF/GLB.

---

## Generating the IFC (the part that bites)

Build IFC4 with **ifcopenshell**. It is **not** in the QGIS Python — it IS on the **PyNET host**
(Civil 3D / Navisworks CPython 3.10, `ifcopenshell 0.8.5`). So generate via `send_command` on the
running host, or run a standalone script with a Python that has ifcopenshell. `zipfile` is
whitelisted; `numpy`/`getattr` are **not** (validator), though numpy is installed.

### Hard requirements (or nothing renders)

1. **Tessellated geometry only.** The viewer renders `IfcTriangulatedFaceSet` with representation
   type **`"Tessellation"`**. `IfcExtrudedAreaSolid` / `"SweptSolid"` does **NOT** render — this was
   the root cause of "no geometry". Build every shape as triangle meshes (`IfcCartesianPointList3D`
   + `IfcTriangulatedFaceSet`), exactly like `NavisworksPNT_IFC_Fast.py`.
2. **Colour via `IfcSurfaceStyleRendering`** on the tri-set: `IfcStyledItem(triSet, [IfcSurfaceStyle("BOTH",
   [IfcSurfaceStyleRendering(IfcColourRgb(...), 0.0, ..., "FLAT")])])`. RGB are floats 0..1.
3. **Double-side every mesh.** web-ifc back-face culls → geometry disappears when orbiting. Emit each
   triangle twice, once reversed: `faces + [(a, c, b) for (a, b, c) in faces]`.
4. **ifcopenshell 0.8.5 wants tuples, not lists.** `createIfcCartesianPointList3D(tuple(tuple(floats)))`
   and the `CoordIndex` as a tuple of tuples — list-of-lists raises a `TypeError` (AGGREGATE OF
   AGGREGATE OF DOUBLE).
5. **Subtract a local origin.** Keep coordinates near 0 (subtract the min X/Y/Z). Real UTM values
   (~6.3e5 / 4.6e6) overflow float32 precision on the GPU → vertex jitter. Real *scale* (a 7 km
   extent) is fine as long as the origin is local.

### Skeleton (low-level, version-stable)

```python
ifc = ifcopenshell.file(schema="IFC4")
units = ifc.createIfcUnitAssignment([ifc.createIfcSIUnit(None,"LENGTHUNIT",None,"METRE"),
                                     ifc.createIfcSIUnit(None,"AREAUNIT",None,"SQUARE_METRE"),
                                     ifc.createIfcSIUnit(None,"VOLUMEUNIT",None,"CUBIC_METRE")])
ax2p = ifc.createIfcAxis2Placement3D(pt([0,0,0]), dir([0,0,1]), dir([1,0,0]))
ctx  = ifc.createIfcGeometricRepresentationContext(None,"Model",3,1e-5,ax2p,None)
bctx = ifc.createIfcGeometricRepresentationSubContext("Body","Model",None,None,None,None,ctx,None,"MODEL_VIEW",None)
proj = ifc.createIfcProject(guid(),None,name,None,None,None,None,[ctx],units)
# site → building → storey via IfcLocalPlacement(None, IfcAxis2Placement3D(origin)) + IfcRelAggregates
# per element: triSet → IfcShapeRepresentation(bctx,"Body","Tessellation",[triSet])
#              → IfcProductDefinitionShape → IfcBuildingElementProxy(world_placement)
# finally: IfcRelContainedInSpatialStructure(..., proxies, storey); ifc.write(path)
```

Package with `zipfile`: `z.write(ifc_path, "models/riesgo.ifc")` + `z.writestr("clashes.json", ...)`.

### The fire-risk twin generator (current state)

Reads the QGIS outputs in `04_QGIS/output/<slug>/` (`prioridad_segmentos.json`,
`riesgo_incendio.json`, `desbroce_aerogeneradores.json`) and the live Civil 3D **TinSurface**:

- **Terrain**: sample `TinSurface.FindElevationAtXY` on a ~70 m grid → one tessellated mesh.
- **AT line / heatmap / turbines**: draped on the terrain (z from the surface), as coloured boxes
  (risk → green/yellow/orange/red; turbines → priority colour).
- Generated inline via `send_command` (not yet saved to disk — TODO: save as a reusable script; it
  runs on the host, not QGIS, so it does **not** belong in `04_QGIS`).

---

## Known limitation — viewer far-plane (TODO before real-scale)

The viewer camera (`03_Viewer/src/main.ts`, ~line 61) sets `threePersp.near = 0.01` and leaves the
default `far` (**2000**). A geographic model (~7 km) is clipped beyond 2 km → geometry "disappears
when moving". Current stop-gap was scaling the model ×0.1 (a navigable "maquette" — but loses real
scale/measurement).

**Proper fix** (no performance cost — `far` doesn't add draw calls; raising `near` improves depth
precision; origin-subtracted coords avoid jitter):

```ts
world.camera.threePersp.near = 1;        // was 0.01
world.camera.threePersp.far  = 200000;   // was default 2000 → 200 km
world.camera.threePersp.updateProjectionMatrix();
```

Then rebuild the viewer (vite → `dist/`) and regenerate the `.pnt` at **real scale (S = 1)**, no ×0.1.

---

## Quick checklist

- [ ] IFC built with `IfcTriangulatedFaceSet` + `"Tessellation"` (never SweptSolid)
- [ ] Colour via `IfcSurfaceStyleRendering`, RGB 0..1
- [ ] Every mesh double-sided (reversed faces appended)
- [ ] Tuples (not lists) into `createIfcCartesianPointList3D` / `CoordIndex`
- [ ] Coordinates origin-subtracted (near 0)
- [ ] `clashes.json` with `models[].fileName`; IFC under `models/`
- [ ] Load with `viewer_load_package` → `viewer_fit`
