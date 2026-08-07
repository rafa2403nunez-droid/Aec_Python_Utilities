import * as THREE from "three";
import * as FRAGS from "@thatopen/fragments";
import * as OBC from "@thatopen/components";
import * as OBF from "@thatopen/components-front";
import * as BUI from "@thatopen/ui";
import { viewportGridTemplate } from "./ui-templates/grids/viewport";
import { viewportSettingsTemplate } from "./ui-templates/buttons/viewport-settings";
import { measurementsPanelTemplate } from "./ui-templates/panels/measurements-panel";
import { sectionPanelTemplate, TOGGLE_SECTION_MODE } from "./ui-templates/panels/section-panel";
import { propertiesPanelTemplate, PROPERTIES_DATA_EVENT, PropertiesData } from "./ui-templates/panels/properties-panel";
import { treePanelTemplate } from "./ui-templates/panels/spatial-tree-panel";
import { createViewCube } from "./viewcube";
import { getConfig } from "./config";
import { loadModelFromUrl, loadAllModels, LoaderContext } from "./loader";

BUI.Manager.init();
document.documentElement.style.setProperty("--bim-ui_main-base", "#4388B1");
document.documentElement.style.setProperty("--bim-ui_accent-base", "#4388B1");

const components = new OBC.Components();
const worlds = components.get(OBC.Worlds);

const world = worlds.create<
  OBC.SimpleScene,
  OBC.OrthoPerspectiveCamera,
  OBF.PostproductionRenderer
>();

world.name = "Main";
world.scene = new OBC.SimpleScene(components);
world.scene.setup();

// Navisworks-style gradient background (lighter blue top → dark navy bottom)
const _bgCanvas = document.createElement("canvas");
_bgCanvas.width = 2;
_bgCanvas.height = 256;
const _bgCtx = _bgCanvas.getContext("2d")!;
const _bgGrad = _bgCtx.createLinearGradient(0, 0, 0, 256);
_bgGrad.addColorStop(0, "#3a6a9e");
_bgGrad.addColorStop(1, "#1a304d");
_bgCtx.fillStyle = _bgGrad;
_bgCtx.fillRect(0, 0, 2, 256);
const _bgTex = new THREE.CanvasTexture(_bgCanvas);
world.scene.three.background = _bgTex;

const viewport = BUI.Component.create<BUI.Viewport>(() => {
  return BUI.html`<bim-viewport></bim-viewport>`;
});

// Mount viewport to DOM BEFORE creating renderer — otherwise framebuffers init at 0x0
const app = document.getElementById("app")!;
app.style.display = "flex";
app.style.width = "100%";
app.style.height = "100vh";
viewport.style.flex = "1";
viewport.style.width = "100%";
viewport.style.height = "100%";
app.appendChild(viewport);

world.renderer = new OBF.PostproductionRenderer(components, viewport);
world.camera = new OBC.OrthoPerspectiveCamera(components);
world.camera.threePersp.near = 0.01;
world.camera.threePersp.updateProjectionMatrix();
world.camera.controls.restThreshold = 0.05;

// Adapt the camera clip planes to the loaded extent. Giant models (infrastructure, whole
// sites) get clipped away by a fixed far plane — so scale far to the model's diagonal.
// Raising far is free (it adds no triangles/draw calls); near is scaled with the model so
// depth-buffer precision stays reasonable, clamped so small detail up close still renders.
function _updateCameraClipping(): void {
  try {
    const boxer = components.get(OBC.BoundingBoxer);
    boxer.list.clear();
    boxer.addFromModels();
    const box = boxer.get();
    boxer.list.clear();
    if (box.isEmpty()) return;
    const diagonal = box.getSize(new THREE.Vector3()).length();
    if (!isFinite(diagonal) || diagonal <= 0) return;

    const far = Math.max(2000, diagonal * 4);
    const near = Math.min(1, Math.max(0.01, diagonal / 50000));
    for (const cam of [world.camera.threePersp, world.camera.threeOrtho]) {
      if (!cam) continue;
      cam.near = near;
      cam.far = far;
      cam.updateProjectionMatrix();
    }
    console.log(`[PNT] camera clipping: near=${near.toFixed(3)} far=${far.toFixed(0)} (diagonal=${diagonal.toFixed(0)})`);
  } catch (e) {
    console.warn("[PNT] camera clipping update failed", e);
  }
}

// No grid

const resizeWorld = () => {
  world.renderer?.resize();
  world.camera.updateAspect();
};

viewport.addEventListener("resize", resizeWorld);

world.dynamicAnchor = false;

components.init();

components.get(OBC.Raycasters).get(world);

const { postproduction } = world.renderer;
postproduction.enabled = true;
postproduction.style = OBF.PostproductionAspect.COLOR_SHADOWS;

const { aoPass, edgesPass } = world.renderer.postproduction;

edgesPass.color = new THREE.Color(0x494b50);

const aoParameters = {
  radius: 0.25,
  distanceExponent: 1,
  thickness: 1,
  scale: 1,
  samples: 16,
  distanceFallOff: 1,
  screenSpaceRadius: true,
};

const pdParameters = {
  lumaPhi: 10,
  depthPhi: 2,
  normalPhi: 3,
  radius: 4,
  radiusExponent: 1,
  rings: 2,
  samples: 16,
};

aoPass.updateGtaoMaterial(aoParameters);
aoPass.updatePdMaterial(pdParameters);

const fragments = components.get(OBC.FragmentsManager);
fragments.init("./worker/worker.mjs");

fragments.core.models.materials.list.onItemSet.add(({ value: material }) => {
  const isLod = "isLodMaterial" in material && material.isLodMaterial;
  if (isLod) {
    world.renderer!.postproduction.basePass.isolatedMaterials.push(material);
  }
  // IFC geometry exported from Navisworks can have inward-facing normals
  (material as any).side = THREE.DoubleSide;
});

world.camera.projection.onChanged.add(() => {
  for (const [_, model] of fragments.list) {
    model.useCamera(world.camera.three);
  }
});

world.camera.controls.addEventListener("rest", () => {
  fragments.core.update(true);
});

const ifcLoader = components.get(OBC.IfcLoader);
await ifcLoader.setup({
  autoSetWasm: false,
  wasm: { absolute: true, path: "https://unpkg.com/web-ifc@0.0.71/" },
});

// Our own IfcImporter, configured identically to the one IfcLoader builds internally on
// each .load() call (mirrors its settings.wasm.* / settings.webIfc) — built eagerly here
// instead of waiting on IfcLoader.onIfcImporterInitialized, which only fires from inside
// .load() and is therefore never populated before the first model load.
const ifcImporter = new FRAGS.IfcImporter();
ifcImporter.wasm.path = ifcLoader.settings.wasm.path;
ifcImporter.wasm.absolute = ifcLoader.settings.wasm.absolute;
ifcImporter.webIfcSettings = ifcLoader.settings.webIfc;

fragments.core.settings.autoCoordinate = true;

const loaderCtx: LoaderContext = {
  fragments,
  ifcImporter,
  camera: world.camera.three,
};

const hider = components.get(OBC.Hider);

// The pnt_id of whatever is currently under the "select" highlight (click in the 3D view, the
// tree panel, or an MCP-driven viewer_select) — reported to the bridge via _reportViewerState()
// so viewer_get_state can answer "what's currently selected".
let _lastSelectedPntId: string | null = null;

const highlighter = components.get(OBF.Highlighter);
highlighter.setup({
  world,
  selectMaterialDefinition: {
    color: new THREE.Color("#bcf124"),
    renderedFaces: 1,
    opacity: 1,
    transparent: false,
  },
});

highlighter.events.select.onHighlight.add(async (map) => {
  const readable = Object.fromEntries(Object.entries(map).map(([k, v]) => [k, [...v]]));
  console.log("[PNT] select onHighlight:", JSON.stringify(readable));

  const modelId = Object.keys(map)[0];
  if (!modelId) return;
  const localIdSet = map[modelId] as Set<number>;
  // A whole-model or type-group node (multiple instances) has no single element's properties to
  // show — picking "the first" out of the Set is arbitrary, not meaningful. Those come from the
  // tree panel, which dispatches its own summary (model/type name + instance count) instead; only
  // resolve real psets here for a genuine single-element pick.
  if (localIdSet.size !== 1) return;
  const [localId] = localIdSet;
  if (localId == null) return;

  const model = fragments.list.get(modelId);
  if (!model) return;

  const guids = await model.getGuidsByLocalIds([localId]);
  const guid = guids?.[0];
  console.log("[PNT] select guid:", guid, "localId:", localId);

  let data: PropertiesData | null = null;
  if (guid) {
    const pntId = _decompressGuid(guid);
    console.log("[PNT] select pntId:", pntId);
    data = _propertiesCache.get(pntId) ?? null;
    _lastSelectedPntId = pntId;
    _reportViewerState();
  }

  window.dispatchEvent(new CustomEvent(PROPERTIES_DATA_EVENT, { detail: data }));
});

highlighter.events.select.onClear.add(() => {
  _lastSelectedPntId = null;
  _reportViewerState();
  window.dispatchEvent(new CustomEvent(PROPERTIES_DATA_EVENT, { detail: null }));
});

// Register clash highlight styles via the current API (not deprecated add())
highlighter.styles.set("clash-a", {
  color: new THREE.Color(0xff3333),
  renderedFaces: FRAGS.RenderedFaces.TWO,
  opacity: 0.55,
  transparent: true,
});
highlighter.styles.set("clash-b", {
  color: new THREE.Color(0x33dd55),
  renderedFaces: FRAGS.RenderedFaces.TWO,
  opacity: 0.55,
  transparent: true,
});

// A second neutral highlight (distinct from both clash-a/-b and the default "select" yellow)
// for MCP's viewer_select — a plain "look at these" pointer, not a clash pair, so it must not
// borrow the clash colours or isolate the rest of the model.
highlighter.styles.set("select-b", {
  color: new THREE.Color(0x4a9fd0),
  renderedFaces: FRAGS.RenderedFaces.TWO,
  opacity: 0.6,
  transparent: true,
});

highlighter.events["clash-a"].onHighlight.add((map) => {
  const readable = Object.fromEntries(Object.entries(map).map(([k, v]) => [k, [...v]]));
  console.log("[PNT] clash-a onHighlight fired:", JSON.stringify(readable));
});

// Clipper Setup
const clipper = components.get(OBC.Clipper);
viewport.ondblclick = async () => {
  if (!clipper.enabled) return;
  const plane = await clipper.create(world) as any;
  if (!plane) return;

  // Offset the plane slightly outward from the clicked surface (in normal direction)
  // so the plane rectangle doesn't overlap the mesh face.
  const PLANE_OFFSET = 1; // metres (IFC model units) — negative = behind the face normal
  const offsetOrigin = (plane.origin as THREE.Vector3).clone()
    .add((plane.normal as THREE.Vector3).clone().multiplyScalar(-PLANE_OFFSET));
  plane.setFromNormalAndCoplanarPoint((plane.normal as THREE.Vector3).clone(), offsetOrigin);

  const controls = plane._controls as any;
  // Patch gizmo.updateMatrixWorld so Lines are always hidden AFTER its own visibility logic runs.
  // updateMatrixWorld executes before THREE.js builds the render list, so visible=false here
  // guarantees Lines are never queued for rendering — colorWrite doesn't help because
  // the PostproductionRenderer resets GL state between passes.
  const gizmo = (controls as any)?._gizmo;
  if (gizmo && !gizmo._linesPatchApplied) {
    gizmo._linesPatchApplied = true;
    const orig = gizmo.updateMatrixWorld.bind(gizmo);
    gizmo.updateMatrixWorld = (force?: boolean) => {
      orig(force);
      gizmo.traverse((obj: THREE.Object3D) => {
        if (obj.type === "Line" || obj.type === "LineSegments") obj.visible = false;
      });
    };
  }
};

window.addEventListener("keydown", (event) => {
  if (event.code === "Delete" || event.code === "Backspace") {
    clipper.delete(world);
  }
});

// Length Measurement Setup
const lengthMeasurer = components.get(OBF.LengthMeasurement);
lengthMeasurer.world = world;
lengthMeasurer.color = new THREE.Color("#4388B1");

lengthMeasurer.list.onItemAdded.add((line) => {
  const center = new THREE.Vector3();
  line.getCenter(center);
  const radius = line.distance() / 3;
  const sphere = new THREE.Sphere(center, radius);
  world.camera.controls.fitToSphere(sphere, true);
});

viewport.addEventListener("dblclick", () => lengthMeasurer.create());

window.addEventListener("keydown", (event) => {
  if (event.code === "Delete" || event.code === "Backspace") {
    lengthMeasurer.delete();
  }
});

// Area Measurement Setup
const areaMeasurer = components.get(OBF.AreaMeasurement);
areaMeasurer.world = world;
areaMeasurer.color = new THREE.Color("#4388B1");

areaMeasurer.list.onItemAdded.add((area) => {
  if (!area.boundingBox) return;
  const sphere = new THREE.Sphere();
  area.boundingBox.getBoundingSphere(sphere);
  world.camera.controls.fitToSphere(sphere, true);
});

viewport.addEventListener("dblclick", () => {
  areaMeasurer.create();
});

window.addEventListener("keydown", (event) => {
  if (event.code === "Enter" || event.code === "NumpadEnter") {
    areaMeasurer.endCreation();
  }
});

// ─── PNT Clash Highlight System ───────────────────────────────────────────────

// Compress pnt_id (32-char hex UUID) → 22-char IFC GlobalId
// Mirrors ifcopenshell.guid.compress: standard base64 with IFC charset translation
const _B64_STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
const _B64_IFC = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_$";

function _compressGuid(hex: string): string {
  const padded = "0000" + hex.toLowerCase();
  const bytes = [];
  for (let i = 0; i < padded.length; i += 2)
    bytes.push(parseInt(padded.slice(i, i + 2), 16));
  const b64std = btoa(bytes.map(b => String.fromCharCode(b)).join(""));
  return b64std.slice(2).split("").map(c => _B64_IFC[_B64_STD.indexOf(c)]).join("");
}

// Reverse: 22-char IFC GlobalId → 32-char hex pnt_id
function _decompressGuid(compressed: string): string {
  const b64ifc = compressed.split("").map(c => _B64_STD[_B64_IFC.indexOf(c)]).join("");
  // Original base64 string started with "AA" (bytes 0,1 = 0x00,0x00) before slice(2)
  const raw = atob("AA" + b64ifc);
  let hex = "";
  for (let i = 0; i < raw.length; i++)
    hex += raw.charCodeAt(i).toString(16).padStart(2, "0");
  return hex.slice(4); // strip "0000" prefix (4 hex chars)
}

// Queue of model names populated just before each load — consumed by onItemSet
const _pendingNames: string[] = [];

// Properties lookup cache: pnt_id (32-char hex) → entry from properties.json
const _propertiesCache = new Map<string, PropertiesData>();
// Baked-in true-north rotation (radians) written by the exporter under properties.json["__meta__"].
// Drives the ViewCube so Front/Side snap to the building, not the world axes.
let _viewNorthRad = 0;
fetch("/data/properties.json")
  .then(r => r.json())
  .then((data: Record<string, any>) => {
    for (const [pntId, entry] of Object.entries(data)) {
      if (pntId.startsWith("__")) continue; // reserved meta keys, not elements
      _propertiesCache.set(pntId, entry as PropertiesData);
    }
    const meta = data["__meta__"];
    const deg = meta?.viewRotationDeg ?? meta?.northAngleDeg;
    if (typeof deg === "number") {
      _viewNorthRad = (deg * Math.PI) / 180;
      console.log(`[PNT] view rotation: ${deg}°`);
    }
    console.log(`[PNT] properties loaded: ${_propertiesCache.size} entries`);
  })
  .catch(() => console.warn("[PNT] properties.json not available"));

// Resolve one or more pnt_ids (32-char hex) to a ModelIdMap (modelId → localId set) by
// compressing each to its IFC GlobalId and looking it up across the loaded models.
async function _resolvePntIds(pntIds: string | string[]): Promise<OBC.ModelIdMap> {
  const sel: OBC.ModelIdMap = {};
  const ids = Array.isArray(pntIds) ? pntIds : [pntIds];
  for (const pntId of ids) {
    const compressed = _compressGuid(pntId);
    for (const [modelId, model] of fragments.list) {
      const localIds = await model.getLocalIdsByGuids([compressed]);
      const localId = localIds?.[0];
      if (localId != null) {
        if (!sel[modelId]) sel[modelId] = new Set();
        (sel[modelId] as Set<number>).add(localId);
        break;
      }
    }
  }
  return sel;
}

async function _highlightClash(
  pntIdA: string | string[] | null,
  pntIdB: string | string[] | null,
): Promise<void> {
  try { highlighter.clear("clash-a"); } catch (_) {}
  try { highlighter.clear("clash-b"); } catch (_) {}
  try { highlighter.clear("select"); } catch (_) {}
  try { highlighter.clear("select-b"); } catch (_) {}
  await hider.set(true); // undo any prior isolate

  if (!pntIdA && !pntIdB) return;

  const selA: OBC.ModelIdMap = pntIdA ? await _resolvePntIds(pntIdA) : {};
  const selB: OBC.ModelIdMap = pntIdB ? await _resolvePntIds(pntIdB) : {};

  const hasA = Object.keys(selA).length > 0;
  const hasB = Object.keys(selB).length > 0;
  if (!hasA && !hasB) return;

  if (hasA) await highlighter.highlightByID("clash-a", selA, !hasB, false);
  if (hasB) await highlighter.highlightByID("clash-b", selB, true, false);

  // Isolate (hide, not ghost) the clash pair instead of dimming everything else — with
  // 5 federated disciplines loaded, thousands of overlapping semi-transparent surfaces
  // don't depth-sort cleanly in WebGL and the "ghost" look turns into visual noise.
  const focusMap: OBC.ModelIdMap = {};
  for (const sel of [selA, selB]) {
    for (const [modelId, ids] of Object.entries(sel)) {
      if (!focusMap[modelId]) focusMap[modelId] = new Set<number>();
      for (const id of ids as Set<number>) (focusMap[modelId] as Set<number>).add(id);
    }
  }
  if (!OBC.ModelIdMapUtils.isEmpty(focusMap)) {
    // hider.isolate() runs its hide-all and show-selected calls concurrently (Promise.all
    // internally), which races on models shared between the two — sequence them ourselves.
    await hider.set(false);
    await hider.set(true, focusMap);
    await fragments.core.update(true);
    await world.camera.fitToItems(focusMap);
  }
}

// Plain "look at these elements" selection for MCP's viewer_select — neutral colours
// (select / select-b), no isolation of the rest of the model. Distinct from _highlightClash,
// which is specifically for clash pairs (red/green + isolate).
async function _selectPntIds(
  pntIdsA: string | string[] | null,
  pntIdsB: string | string[] | null,
): Promise<void> {
  try { highlighter.clear("clash-a"); } catch (_) {}
  try { highlighter.clear("clash-b"); } catch (_) {}
  try { highlighter.clear("select"); } catch (_) {}
  try { highlighter.clear("select-b"); } catch (_) {}
  await hider.set(true); // undo any prior isolate — this is a plain select, never isolated

  if (!pntIdsA && !pntIdsB) return;

  const selA: OBC.ModelIdMap = pntIdsA ? await _resolvePntIds(pntIdsA) : {};
  const selB: OBC.ModelIdMap = pntIdsB ? await _resolvePntIds(pntIdsB) : {};

  const hasA = Object.keys(selA).length > 0;
  const hasB = Object.keys(selB).length > 0;
  if (!hasA && !hasB) return;

  if (hasA) await highlighter.highlightByID("select", selA, true, false);
  if (hasB) await highlighter.highlightByID("select-b", selB, false, false);

  const focusMap: OBC.ModelIdMap = {};
  for (const sel of [selA, selB]) {
    for (const [modelId, ids] of Object.entries(sel)) {
      if (!focusMap[modelId]) focusMap[modelId] = new Set<number>();
      for (const id of ids as Set<number>) (focusMap[modelId] as Set<number>).add(id);
    }
  }
  if (!OBC.ModelIdMapUtils.isEmpty(focusMap)) await world.camera.fitToItems(focusMap);
}

// Isolate (hide everything except) the given pnt_ids. Undo with a "clear" command or the
// toolbar's Show All / Reset Visibility.
async function _isolatePntIds(pntIds: string | string[] | null): Promise<void> {
  if (!pntIds || (Array.isArray(pntIds) && pntIds.length === 0)) return;
  const sel = await _resolvePntIds(pntIds);
  if (OBC.ModelIdMapUtils.isEmpty(sel)) {
    console.warn("[PNT] isolate: none of the pnt_ids resolved to a loaded element");
    return;
  }
  await hider.set(false);
  await hider.set(true, sel);
  await fragments.core.update(true);
}

// Show only the named model(s) (whole discipline, e.g. "Snowdon Towers Sample HVAC"), hide the
// rest — a model-level isolate, cheaper than resolving every element's pnt_id one by one for a
// "just show me this discipline" request. Model names come from viewer_get_state's "models" list.
async function _isolateModels(modelNames: string | string[] | null): Promise<void> {
  const names = new Set(
    Array.isArray(modelNames) ? modelNames : modelNames ? [modelNames] : [],
  );
  if (names.size === 0) return;
  for (const [modelId, model] of fragments.list) {
    await model.setVisible(undefined, names.has(modelId));
  }
  await fragments.core.update(true);
  _updateCameraClipping();
  await world.camera.fitToItems();
}

// ─── Fragments model loaded ───────────────────────────────────────────────────

fragments.list.onItemSet.add(async ({ key: modelId, value: model }) => {
  model.useCamera(world.camera.three);
  model.getClippingPlanesEvent = () => {
    return Array.from(world.renderer!.three.clippingPlanes) || [];
  };
  world.scene.three.add(model.object);
  await fragments.core.update(true);
  _updateCameraClipping();
  await world.camera.fitToItems();

  _pendingNames.shift();
  console.log(`[PNT] model ready: ${modelId}`);
  _reportViewerState();
});

// Viewport Layouts
const [viewportSettings] = BUI.Component.create(viewportSettingsTemplate, {
  components,
  world,
});

viewport.append(viewportSettings);

const [viewportGrid] = BUI.Component.create(viewportGridTemplate, {
  components,
  world,
});

viewport.append(viewportGrid);

const [measurementsPanel] = BUI.Component.create(measurementsPanelTemplate, {
  components,
  lengthUnit: "m" as const,
  areaUnit: "m2" as const,
});

viewport.append(measurementsPanel);

const [sectionPanel] = BUI.Component.create(sectionPanelTemplate, {
  components,
  world,
  mode: "translate" as const,
});

viewport.append(sectionPanel);

const [propertiesPanel] = BUI.Component.create(propertiesPanelTemplate, {});

viewport.append(propertiesPanel);

const [treePanel] = BUI.Component.create(treePanelTemplate, { components });

viewport.append(treePanel);

createViewCube(world.camera, viewport, () => _viewNorthRad);

window.addEventListener("keydown", (event) => {
  if (event.code === "KeyR" && !event.repeat) {
    window.dispatchEvent(new Event(TOGGLE_SECTION_MODE));
  }
});

// ─── Public API ───────────────────────────────────────────────────────────────

declare global {
  interface Window {
    loadModel: (url: string, name?: string) => Promise<void>;
    highlightElements: (modelId: string, expressIds: number[]) => Promise<void>;
    fitToAllModels: () => Promise<void>;
    highlightClash: (pntIdA: string | string[] | null, pntIdB: string | string[] | null) => Promise<void>;
  }
}

window.loadModel = async (url: string, name?: string) => {
  await loadModelFromUrl(loaderCtx, url, name);
};

window.highlightElements = async (modelId: string, expressIds: number[]) => {
  const selection: OBC.ModelIdMap = {};
  selection[modelId] = new Set(expressIds);
  await highlighter.highlightByID("select", selection, true, true);
};

window.fitToAllModels = async () => {
  await world.camera.fitToItems();
};

window.highlightClash = _highlightClash;

// Listen for postMessage from parent (dashboard iframe communication)
window.addEventListener("message", async (event) => {
  if (!event.data || event.data.type !== "viewer-command") return;

  console.log("[Viewer] command received:", event.data.action, event.data.payload);

  const { action, payload } = event.data;

  switch (action) {
    case "loadModel": {
      const stem = (payload.url as string).split("/").pop()?.replace(".ifc", "") ?? payload.name ?? "";
      if (stem) _pendingNames.push(stem);
      try {
        await window.loadModel(payload.url, payload.name);
      } catch (err) {
        _reportLoadError(stem || payload.name || payload.url, err);
      }
      break;
    }
    case "highlightElements":
      await window.highlightElements(payload.modelId, payload.expressIds);
      break;
    case "fitToAllModels":
      await window.fitToAllModels();
      break;
    case "clearHighlight":
      try { highlighter.clear("clash-a"); } catch (_) {}
      try { highlighter.clear("clash-b"); } catch (_) {}
      try { highlighter.clear("select"); } catch (_) {}
      try { highlighter.clear("select-b"); } catch (_) {}
      await hider.set(true);
      await fragments.core.update(true);
      break;
    case "highlightClash":
      await _highlightClash(
        payload.pnt_id_a ?? null,
        payload.pnt_id_b ?? null,
      );
      break;
  }
});

// ─── MCP control channel (SSE) ─────────────────────────────────────────────────
// The local pnt_server fans out commands (POSTed to /api/control by the MCP bridge)
// to this viewer over Server-Sent Events. Maps server actions onto the same window.*
// API used by the postMessage path above. See pnt_server.py /api/control + /api/events.
async function _applyControlCommand(action: string, payload: any): Promise<void> {
  switch (action) {
    case "load_model": {
      const stem = (payload.url as string)?.split("/").pop()?.replace(".ifc", "") ?? payload.name ?? "";
      if (stem) _pendingNames.push(stem);
      try {
        await window.loadModel(payload.url, payload.name);
      } catch (err) {
        _reportLoadError(stem || payload.name || payload.url, err);
      }
      break;
    }
    case "select":
      if (payload.pnt_id_a || payload.pnt_id_b) {
        await _highlightClash(payload.pnt_id_a ?? null, payload.pnt_id_b ?? null);
      } else if (payload.modelId) {
        await window.highlightElements(payload.modelId, payload.expressIds ?? []);
      }
      break;
    case "select_ids":
      await _selectPntIds(payload.pnt_id_a ?? null, payload.pnt_id_b ?? null);
      break;
    case "fit":
      await window.fitToAllModels();
      break;
    case "clear":
      try { highlighter.clear("clash-a"); } catch (_) {}
      try { highlighter.clear("clash-b"); } catch (_) {}
      try { highlighter.clear("select"); } catch (_) {}
      try { highlighter.clear("select-b"); } catch (_) {}
      await hider.set(true); // undo any prior isolate/hide
      await fragments.core.update(true);
      break;
    case "isolate":
      await _isolatePntIds(payload.pnt_ids ?? payload.pnt_id_a ?? null);
      break;
    case "isolate_models":
      await _isolateModels(payload.models ?? payload.model ?? null);
      break;
  }
  _reportViewerState();
}

// Surface a load failure (missing dependency, corrupt IFC, WASM fetch failure, etc.) to the
// VS Code host — otherwise it's just an unhandled rejection buried in the webview's devtools
// console, invisible behind the "loading model…" notification that already closed.
function _reportLoadError(model: string, err: unknown): void {
  const message = err instanceof Error ? err.message : String(err);
  console.error(`[PNT] failed to load ${model}:`, err);
  window.parent?.postMessage(
    { type: "viewer-event", event: "loadError", model, message },
    "*",
  );
}

// Report the viewer's current state so the bridge's get_state can read it back.
function _reportViewerState(): void {
  const models = [...fragments.list.keys()];
  fetch("/api/state", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ type: "viewer-state", models, selected: _lastSelectedPntId }),
  }).catch(() => { /* server may not be the pnt_server (e.g. vite dev) */ });
}

try {
  const _sse = new EventSource("/api/events");
  _sse.onmessage = (ev) => {
    if (!ev.data) return;
    try {
      const cmd = JSON.parse(ev.data);
      if (cmd.action) _applyControlCommand(cmd.action, cmd.payload ?? cmd);
    } catch (e) {
      console.warn("[PNT] bad control command", e);
    }
  };
  _sse.onerror = () => { /* EventSource auto-reconnects */ };
  console.log("[PNT] control channel connected (/api/events)");
} catch (e) {
  console.warn("[PNT] control channel unavailable", e);
}

// ─── Auto-load models from config ───

const config = getConfig();

if (config.autoLoad && config.modelUrls.length > 0) {
  // Pre-populate name queue so onItemSet can identify each model reliably
  for (const url of config.modelUrls) {
    const stem = url.split("/").pop()?.replace(".ifc", "") ?? "";
    if (stem) _pendingNames.push(stem);
  }
  loadAllModels(config, loaderCtx, (loaded, total, name) => {
    console.log(`[PyNET Viewer] Progress: ${loaded}/${total} — ${name}`);
  }).then(() => {
    console.log("[PyNET Viewer] All models loaded");
    _updateCameraClipping();
    world.camera.fitToItems();
    window.parent?.postMessage(
      { type: "viewer-event", event: "modelsLoaded" },
      "*",
    );
  }).catch((err) => _reportLoadError(config.modelUrls.join(", "), err));
}
