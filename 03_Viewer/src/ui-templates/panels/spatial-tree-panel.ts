import * as BUI from "@thatopen/ui";
import * as OBC from "@thatopen/components";
import * as OBF from "@thatopen/components-front";
import { PROPERTIES_DATA_EVENT, type PropertiesData } from "./properties-panel";

export const TOGGLE_TREE_PANEL = "toggle-tree-panel";
export let treePanelVisible = false;

// ─── Tree model ─────────────────────────────────────────────────────────────────
interface TreeNode {
  id: string;
  modelId: string;
  label: string;
  ref?: string;       // element's own unique id (Revit Tag / IFC GlobalId) — shown for instances
  category?: string;  // Revit category of an instance — groups the Category level above Type
  kind?: "category" | "type"; // grouping nodes only; used to label the Properties panel
  localIds: number[]; // every element localId under this node — used for select/hide/isolate
  children: TreeNode[];
}

// Revit-style hierarchy: Model · Level · Category · Type · Instances. Everything above the storey
// (Project / Site / Building / infra facilities) is dropped as noise — we lift its children.
const DROP_ABOVE_LEVEL = new Set([
  "IFCPROJECT", "IFCSITE", "IFCBUILDING", "IFCSPACE", "IFCEXTERNALSPATIALELEMENT",
  "IFCFACILITY", "IFCFACILITYPART", "IFCBRIDGE", "IFCBRIDGEPART",
  "IFCROAD", "IFCROADPART", "IFCRAILWAY", "IFCRAILWAYPART", "IFCMARINEFACILITY",
]);
// The "Level" of the tree.
const LEVEL_CATEGORIES = new Set(["IFCBUILDINGSTOREY", "IFCSTOREY"]);

// Inline SVG icons (rendered eagerly, unlike iconify's lazy load — no hover delay).
const _icoEye = BUI.html`<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M12 5c-5 0-9.3 3.1-11 7 1.7 3.9 6 7 11 7s9.3-3.1 11-7c-1.7-3.9-6-7-11-7Zm0 12a5 5 0 1 1 0-10 5 5 0 0 1 0 10Zm0-8a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z"/></svg>`;
const _icoEyeOff = BUI.html`<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M2 4.3 4.3 6.6C2.9 7.9 1.8 9.8 1 12c1.7 3.9 6 7 11 7 1.5 0 3-.3 4.3-.8l1.4 1.5L19 22 3.3 3 2 4.3Zm7.5 7.5 2.7 2.7a3 3 0 0 1-2.7-2.7ZM12 7c2.8 0 5 2.2 5 5 0 .5-.1 1-.3 1.5l2.8 2.8c1.2-1.2 2.2-2.7 2.8-4.3-1.7-3.9-6-7-11-7-1 0-2 .2-2.9.5l1.9 1.9c.4-.2.9-.4 1.7-.4Z"/></svg>`;
const _icoIsolate = BUI.html`<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="1.6" fill="currentColor" stroke="none"/></svg>`;

// ── Element-id lookup (from the package's properties.json) ────────────────────────
// The instance's real unique id is the Revit ElementId, carried in properties.json under a
// pset like "ID de elemento" → "Valor" (matches the clash "ID"). We key it by pnt_id and
// resolve each instance's pnt_id from its IFC GlobalId.
const _B64_STD = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
const _B64_IFC = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_$";
function _decompressGuid(compressed: string): string {
  const b64ifc = compressed.split("").map((c) => _B64_STD[_B64_IFC.indexOf(c)]).join("");
  const raw = atob("AA" + b64ifc);
  let hex = "";
  for (let i = 0; i < raw.length; i++) hex += raw.charCodeAt(i).toString(16).padStart(2, "0");
  return hex.slice(4);
}
function _extractElementId(entry: any): string | null {
  const psets = entry?.psets ?? {};
  for (const [pname, pvals] of Object.entries<any>(psets)) {
    if (!/id/i.test(pname) || !/(elemento|element)/i.test(pname)) continue;
    if (pvals && typeof pvals === "object") {
      for (const [k, v] of Object.entries(pvals)) {
        if (/valor|value/i.test(k) && v != null) return String(v);
      }
    }
  }
  return null;
}
// The Revit category ("Barandales superiores", "Muros", …) — the level above Type in the tree.
// The Navisworks exporter writes it on every element under the "Componente" pset (and mirrors it
// on "Tipo"); we prefer those two and fall back to any pset carrying a Category key.
const _CAT_PSETS = [/^(componente|component|elemento|element)$/i, /^(tipo|type)$/i];
const _CAT_KEY = /^categor(í|i)a$|^category$/i;
function _extractCategory(entry: any): string | null {
  const psets = entry?.psets ?? {};
  const pick = (pvals: any): string | null => {
    if (!pvals || typeof pvals !== "object") return null;
    for (const [k, v] of Object.entries(pvals)) {
      if (!_CAT_KEY.test(k) || v == null) continue;
      const s = String(v).trim();
      if (s && s !== "?") return s;
    }
    return null;
  };
  for (const rx of _CAT_PSETS) {
    for (const [pname, pvals] of Object.entries<any>(psets)) {
      if (rx.test(pname)) { const c = pick(pvals); if (c) return c; }
    }
  }
  for (const pvals of Object.values<any>(psets)) { const c = pick(pvals); if (c) return c; }
  return null;
}

const _elementIds = new Map<string, string>();
const _categories = new Map<string, string>();
// Model-root psets (Elemento/Proyecto/Identidad from the Navisworks exporter), keyed by the same
// "m_<stem>" id the tree panel's root TreeNode uses — real project/version/source-path data when
// available, so _selectNode doesn't have to fall back to its synthesized "Name + count" summary.
const _modelPsets = new Map<string, PropertiesData>();
let _propsLoaded = false;
async function _loadProps(): Promise<void> {
  if (_propsLoaded) return;
  _propsLoaded = true;
  try {
    const data = await (await fetch("/data/properties.json")).json();
    for (const [pntId, entry] of Object.entries<any>(data)) {
      if (pntId.startsWith("__")) continue; // reserved meta keys
      if (pntId.startsWith("m_")) { _modelPsets.set(pntId, entry as PropertiesData); continue; }
      const id = _extractElementId(entry);
      if (id) _elementIds.set(pntId, id);
      const cat = _extractCategory(entry);
      if (cat) _categories.set(pntId, cat);
    }
    console.log(
      `[PNT] tree: element ids loaded: ${_elementIds.size}, categories: ${_categories.size},` +
      ` model psets: ${_modelPsets.size}`
    );
  } catch (_) { /* properties.json is optional */ }
}

// ─── Module state ────────────────────────────────────────────────────────────────
let _bimUpdate: BUI.UpdateFunction<TreePanelState> | null = null;
let _components: OBC.Components | null = null;
let _trees: TreeNode[] = [];
let _building = false;
// A model can finish loading (and fire onItemSet) while _buildTrees() is still awaiting a
// previous model's tree — that call returns early (reentrancy guard) and would otherwise be
// lost forever, since the for-loop below only iterates the modelIds snapshotted at its start.
let _rebuildQueued = false;
const _expanded = new Set<string>();
// Currently hidden element localIds, per model (source of truth for the grey-out state).
const _hidden = new Map<string, Set<number>>();
let _isolatedNodeId: string | null = null;
let _query = "";
let _idCounter = 0;

interface TreePanelState {
  components: OBC.Components;
  _init?: boolean;
}

// ─── Data build (Revit-style flatten of getSpatialStructure) ──────────────────────
const _collect = (nodes: TreeNode[]): number[] => {
  const ids: number[] = [];
  for (const n of nodes) ids.push(...n.localIds);
  return ids;
};

// Group leaf instances by their name → one "Type" node per distinct name (with its instances
// beneath). Single-instance types are wrapped too: the instance's element id lives on the child
// row, so collapsing the wrapper away would make that id unreachable in the tree.
function _groupByName(instances: TreeNode[]): TreeNode[] {
  const groups = new Map<string, TreeNode[]>();
  for (const it of instances) {
    const arr = groups.get(it.label);
    if (arr) arr.push(it); else groups.set(it.label, [it]);
  }
  const out: TreeNode[] = [];
  for (const [name, arr] of groups) {
    // Label each instance by its own unique id (Tag / GlobalId), not a running index.
    const children = arr.map((n) => ({ ...n, label: n.ref || n.label }));
    out.push({
      id: `n${_idCounter++}`, modelId: arr[0].modelId, kind: "type",
      label: `${name} (${arr.length})`, localIds: _collect(arr), children,
    });
  }
  out.sort((a, b) => a.label.localeCompare(b.label));
  return out;
}

// Revit Category level, above Type. Packages with no category data at all (non-Revit sources)
// keep the previous Type-only shape rather than growing an "Uncategorized" bucket for everything.
function _groupByCategory(instances: TreeNode[]): TreeNode[] {
  const groups = new Map<string, TreeNode[]>();
  for (const it of instances) {
    const key = it.category || "";
    const arr = groups.get(key);
    if (arr) arr.push(it); else groups.set(key, [it]);
  }
  if (groups.size === 1 && groups.has("")) return _groupByName(instances);

  const out: TreeNode[] = [];
  for (const [cat, arr] of groups) {
    const children = _groupByName(arr);
    out.push({
      id: `n${_idCounter++}`, modelId: arr[0].modelId, kind: "category",
      label: cat || "Uncategorized", localIds: _collect(children), children,
    });
  }
  out.sort((a, b) => a.label.localeCompare(b.label));
  return out;
}

async function _build(model: any, raw: any): Promise<TreeNode[]> {
  const { localId, category, children } = raw ?? {};
  const built: TreeNode[] = [];
  for (const cr of (children ?? [])) built.push(...await _build(model, cr));

  // Category grouping node (no localId of its own).
  if (localId == null && category) {
    const cat = String(category).toUpperCase();
    if (LEVEL_CATEGORIES.has(cat)) return built;                 // keep the storey items as "levels"
    if (DROP_ABOVE_LEVEL.has(cat)) return built.flatMap((n) => n.children); // drop item, lift children
    // Element category → replace the raw IFC class ("BUILDINGELEMENTPROXY") with Revit-style
    // Category ▸ Type nodes, with the instances beneath each type.
    return _groupByCategory(built);
  }

  // Named item node.
  if (localId != null) {
    let name = String(localId);
    let ref = String(localId);
    let cat = "";
    try {
      const attrs = await model.getItem(localId).getAttributes();
      const nameVal = attrs?.getValue?.("Name");
      if (nameVal != null && String(nameVal).length) name = String(nameVal);
      // Unique per-instance id: Revit ElementId from properties.json, joined via the element's
      // IFC GlobalId. In fragments the guid comes from getGuidsByLocalIds (not an attribute).
      // The same pnt_id keys the Revit category used for the Category grouping level.
      const guids = await model.getGuidsByLocalIds([localId]);
      const guid = guids?.[0];
      if (guid) {
        const pntId = _decompressGuid(String(guid));
        ref = _elementIds.get(pntId) ?? String(guid);
        cat = _categories.get(pntId) ?? "";
      }
    } catch (_) { /* keep localId as label/ref */ }
    return [{
      id: `n${_idCounter++}`, modelId: model.modelId, label: name, ref, category: cat,
      localIds: [localId, ..._collect(built)], children: built,
    }];
  }

  return built;
}

// Per-model tree cache — building a model's subtree means one getAttributes() +
// getGuidsByLocalIds() round-trip per element, so redoing it for every already-loaded
// model each time a NEW model finishes (5 disciplines = 5x the eager work) is what made
// the panel feel frozen on federated packages. Each model is now built once and reused;
// _trees is refreshed (and the UI updated) after each individual model finishes, so the
// tree fills in per-discipline as they load instead of waiting for all of them at once.
const _treeCache = new Map<string, TreeNode>();

async function _buildModelTree(modelId: string, model: any): Promise<TreeNode> {
  let children: TreeNode[] = [];
  try {
    const structure = await model.getSpatialStructure();
    const roots = await _build(model, structure);
    // Drop a redundant single project/model root, lifting its children (Levels).
    children = (roots.length === 1 && roots[0].children.length) ? roots[0].children : roots;
  } catch (e) {
    console.warn("[PNT] tree: getSpatialStructure failed for", modelId, e);
  }
  return { id: `m_${modelId}`, modelId, label: modelId, localIds: _collect(children), children };
}

function _syncTreesFromCache(modelIds: Iterable<string>): void {
  _trees = [...modelIds].map((id) => _treeCache.get(id)).filter((t): t is TreeNode => !!t);
}

async function _buildTrees(): Promise<void> {
  if (!_components) return;
  if (_building) { _rebuildQueued = true; return; }
  _building = true;
  try {
    await _loadProps();
    const fragments = _components.get(OBC.FragmentsManager);
    const modelIds = [...fragments.list.keys()];

    for (const modelId of modelIds) {
      if (_treeCache.has(modelId)) continue;
      const model = fragments.list.get(modelId);
      if (!model) continue;
      const tree = await _buildModelTree(modelId, model);
      _treeCache.set(modelId, tree);
      _expanded.add(tree.id); // expand model roots by default
      _syncTreesFromCache([...fragments.list.keys()]);
      if (_bimUpdate) _bimUpdate(); // paint this model's branch immediately, don't wait for the rest
    }
    _syncTreesFromCache(fragments.list.keys());
  } finally {
    _building = false;
    if (_bimUpdate) _bimUpdate();
    if (_rebuildQueued) {
      _rebuildQueued = false;
      void _buildTrees(); // pick up any model(s) that finished loading mid-build
    }
  }
}

// ─── Visibility / selection ───────────────────────────────────────────────────────
const _hiddenSet = (modelId: string): Set<number> => {
  let s = _hidden.get(modelId);
  if (!s) { s = new Set(); _hidden.set(modelId, s); }
  return s;
};

const _nodeHidden = (node: TreeNode): boolean => {
  if (node.localIds.length === 0) return false;
  const s = _hidden.get(node.modelId);
  if (!s || s.size === 0) return false;
  return node.localIds.every((id) => s.has(id));
};

const _modelIdMap = (node: TreeNode): OBC.ModelIdMap => ({ [node.modelId]: new Set(node.localIds) });

const _fragUpdate = async () => {
  await _components!.get(OBC.FragmentsManager).core.update(true);
};

const _selectNode = (node: TreeNode) => {
  if (!_components || node.localIds.length === 0) return;
  const highlighter = _components.get(OBF.Highlighter);
  highlighter.highlightByID("select", _modelIdMap(node), true, false);

  // A model root or a type-group node spans multiple instances — main.ts's onHighlight only
  // resolves psets for a single-element pick, so dispatch data here instead of leaving the
  // Properties panel showing whatever it last had (or, before this fix, a random instance).
  if (node.localIds.length > 1) {
    const isRoot = node.id === `m_${node.modelId}`;
    // Real Elemento/Proyecto/Identidad data from the Navisworks exporter when available (only
    // for roots — type-group nodes have no equivalent); otherwise fall back to a synthesized
    // summary (older .pnt packages exported before this field existed).
    const rootEntry = isRoot ? _modelPsets.get(node.id) : undefined;
    const rootPsets = rootEntry && Object.keys(rootEntry.psets).length > 0 ? rootEntry : undefined;
    const data: PropertiesData = rootPsets ?? {
      pnt_id: node.id,
      name: node.label,
      model: node.modelId,
      psets: {
        [isRoot ? "Model" : node.kind === "category" ? "Category" : "Type"]: {
          Name: node.label,
          Elements: String(node.localIds.length),
        },
      },
    };
    window.dispatchEvent(new CustomEvent(PROPERTIES_DATA_EVENT, { detail: data }));
  }
};

const _toggleHideNode = async (node: TreeNode) => {
  if (!_components || node.localIds.length === 0) return;
  const hider = _components.get(OBC.Hider);
  const s = _hiddenSet(node.modelId);
  const hidden = _nodeHidden(node);
  // hider.set(visible, map): currently hidden → show (true); currently visible → hide (false).
  await hider.set(hidden, _modelIdMap(node));
  for (const id of node.localIds) hidden ? s.delete(id) : s.add(id);
  _isolatedNodeId = null;
  await _fragUpdate();
  if (_bimUpdate) _bimUpdate();
};

const _toggleIsolateNode = async (node: TreeNode) => {
  if (!_components || node.localIds.length === 0) return;
  const hider = _components.get(OBC.Hider);
  if (_isolatedNodeId === node.id) { await _showAll(); return; }
  await hider.isolate(_modelIdMap(node));
  for (const tree of _trees) {
    const s = _hiddenSet(tree.modelId);
    s.clear();
    for (const id of tree.localIds) s.add(id);
    if (tree.modelId === node.modelId) for (const id of node.localIds) s.delete(id);
  }
  _isolatedNodeId = node.id;
  await _fragUpdate();
  if (_bimUpdate) _bimUpdate();
};

async function _showAll(): Promise<void> {
  if (!_components) return;
  await _components.get(OBC.Hider).set(true);
  _hidden.clear();
  _isolatedNodeId = null;
  await _fragUpdate();
  if (_bimUpdate) _bimUpdate();
}

// ─── Search ──────────────────────────────────────────────────────────────────────
const _matches = (node: TreeNode, q: string): boolean => {
  if (!q) return true;
  if (node.label.toLowerCase().includes(q)) return true;
  return node.children.some((c) => _matches(c, q));
};

// ─── Styles ──────────────────────────────────────────────────────────────────────
let _styled = false;
const _ensureStyle = () => {
  if (_styled) return;
  _styled = true;
  const s = document.createElement("style");
  s.textContent = [
    `.pnt-tree,.pnt-tree *{user-select:none;}`,
    `.pnt-tree-row{display:flex;align-items:center;gap:0.25rem;height:1.5rem;padding:0 0.25rem;border-radius:3px;cursor:pointer;white-space:nowrap;overflow:hidden;color:#dfe4ea;}`,
    `.pnt-tree-row:hover{background:rgba(67,136,177,0.20);}`,
    `.pnt-tree-row.pnt-hidden{color:#7b8794;}`,
    `.pnt-tree-caret{flex:0 0 0.9rem;width:0.9rem;text-align:center;font-size:0.5rem;opacity:0.7;cursor:pointer;}`,
    `.pnt-tree-label{flex:1;overflow:hidden;text-overflow:ellipsis;font-size:0.78rem;line-height:1.5rem;cursor:pointer;}`,
    `.pnt-tree-actions{display:flex;gap:0.15rem;flex:0 0 auto;align-items:center;visibility:hidden;}`,
    `.pnt-tree-row:hover .pnt-tree-actions,.pnt-tree-row.pnt-hidden .pnt-tree-actions{visibility:visible;}`,
    `.pnt-tree-act{display:flex;align-items:center;cursor:pointer;opacity:0.6;color:#cfd6de;}`,
    `.pnt-tree-act:hover{opacity:1;color:#4a9fd0;}`,
    `.pnt-tree-act.pnt-act-active{opacity:1;color:#4388B1;}`,
  ].join("");
  document.head.appendChild(s);
};

// ─── Render ──────────────────────────────────────────────────────────────────────
function _renderNode(node: TreeNode, depth: number): BUI.TemplateResult | string {
  if (!_matches(node, _query)) return "";
  const hasChildren = node.children.length > 0;
  const open = _expanded.has(node.id) || _query.length > 0;
  const hidden = _nodeHidden(node);

  const toggle = (e: Event) => {
    e.stopPropagation();
    if (_expanded.has(node.id)) _expanded.delete(node.id);
    else _expanded.add(node.id);
    if (_bimUpdate) _bimUpdate();
  };

  const caret = hasChildren
    ? BUI.html`<span class="pnt-tree-caret" @click=${toggle}>${open ? "▼" : "▶"}</span>`
    : BUI.html`<span class="pnt-tree-caret"></span>`;

  return BUI.html`
    <div class="pnt-tree-row ${hidden ? "pnt-hidden" : ""}" style="padding-left:${0.25 + depth * 0.8}rem"
      @click=${() => _selectNode(node)}>
      ${caret}
      <span class="pnt-tree-label" title=${node.label}>${node.label}</span>
      <span class="pnt-tree-actions">
        <span class="pnt-tree-act" title=${hidden ? "Show" : "Hide"}
          @click=${(e: Event) => { e.stopPropagation(); void _toggleHideNode(node); }}>${hidden ? _icoEyeOff : _icoEye}</span>
        <span class="pnt-tree-act ${_isolatedNodeId === node.id ? "pnt-act-active" : ""}" title="Isolate"
          @click=${(e: Event) => { e.stopPropagation(); void _toggleIsolateNode(node); }}>${_icoIsolate}</span>
      </span>
    </div>
    ${hasChildren && open
      ? BUI.html`<div>${node.children.map((c) => _renderNode(c, depth + 1))}</div>`
      : ""}
  `;
}

export const treePanelTemplate: BUI.StatefullComponent<TreePanelState> = (
  state,
  update,
) => {
  _bimUpdate = update;
  _components = state.components;
  _ensureStyle();

  if (!state._init) {
    state._init = true;
    const fragments = state.components.get(OBC.FragmentsManager);
    fragments.list.onItemSet.add(() => { void _buildTrees(); });
    fragments.list.onItemDeleted.add((modelId: string) => {
      _treeCache.delete(modelId);
      void _buildTrees();
    });
    window.addEventListener(TOGGLE_TREE_PANEL, () => {
      treePanelVisible = !treePanelVisible;
      if (treePanelVisible && _trees.length === 0) void _buildTrees();
      if (_bimUpdate) _bimUpdate();
    });
    if (fragments.list.size > 0) void _buildTrees();
  }

  const onSearch = (e: Event) => {
    _query = ((e.target as BUI.TextInput).value || "").toLowerCase().trim();
    if (_bimUpdate) _bimUpdate();
  };

  // Show whatever branches are already built even while more models are still loading —
  // a federated package fills in per-discipline instead of blocking on all of them.
  const body = _trees.length === 0
    ? BUI.html`<bim-label style="opacity:0.6;font-size:0.75rem;">
        ${_building ? "Building tree…" : "No models loaded."}
      </bim-label>`
    : BUI.html`<div class="pnt-tree">
        ${_trees.map((t) => _renderNode(t, 0))}
        ${_building ? BUI.html`<bim-label style="opacity:0.5;font-size:0.7rem;padding:0.25rem;">Loading more…</bim-label>` : ""}
      </div>`;

  return BUI.html`
    <bim-panel
      label="Models Tree"
      style="
        position: absolute;
        top: 0.5rem;
        bottom: 7rem;
        right: 0.5rem;
        width: 22rem;
        pointer-events: all;
        z-index: 10;
      "
      ?hidden=${!treePanelVisible}
    >
      <bim-panel-section label="Spatial Structure" fixed>
        <div style="display:flex; gap:0.375rem; align-items:center;">
          <bim-text-input @input=${onSearch} vertical placeholder="Search..." debounce="200" style="flex:1;"></bim-text-input>
          <span class="pnt-tree-act" title="Show all" style="padding:0.35rem;"
            @click=${() => void _showAll()}>${_icoEye}</span>
        </div>
        <div style="overflow:auto; margin-top:0.4rem; max-height:calc(100vh - 14rem);">
          ${body}
        </div>
      </bim-panel-section>
    </bim-panel>
  `;
};
