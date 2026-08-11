// SPDX-License-Identifier: MIT
// Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import * as THREE from "three";
import * as BUI from "@thatopen/ui";
import * as OBC from "@thatopen/components";
import * as OBF from "@thatopen/components-front";

export const TOGGLE_SECTION_PANEL = "toggle-section-panel";
export const TOGGLE_SECTION_MODE = "toggle-section-mode";
export let sectionPanelVisible = false;

type SectionMode = "translate" | "rotate";

interface SectionPanelState {
  components: OBC.Components;
  world: OBC.World;
  mode: SectionMode;
  _listenersSet?: boolean;
}

// ── Module-level state ────────────────────────────────────────────────────────
let _bimUpdate: BUI.UpdateFunction<SectionPanelState> | null = null;
let _currentMode: SectionMode = "translate";
// Per-plane rotate change listeners (for cleanup on mode switch)
const _rotateListeners = new Map<string, () => void>();
// Per-plane drag-visibility preservers (restore plane after OBC's changeDrag hides it)
const _dragPreservers = new Map<string, (e: any) => void>();
// Original face normal captured at plane creation (used by Reset)
const _originalNormals = new Map<string, THREE.Vector3>();

// ── Rotate-mode gizmo helpers ─────────────────────────────────────────────────

// Hide the ring whose world axis is most aligned with the plane normal (spinning
// in place around that axis is useless). The defineProperty guard in TransformControls
// (`if (propValue !== value)`) prevents "change" from re-firing when nothing changed.
const updateRingVisibility = (controls: any, normal: THREE.Vector3) => {
  const ax = Math.abs(normal.x), ay = Math.abs(normal.y), az = Math.abs(normal.z);
  let hideX = false, hideY = false, hideZ = false;
  if      (ax >= ay && ax >= az) hideX = true;
  else if (ay >= ax && ay >= az) hideY = true;
  else                           hideZ = true;
  if (controls.showX !== !hideX) controls.showX = !hideX;
  if (controls.showY !== !hideY) controls.showY = !hideY;
  if (controls.showZ !== !hideZ) controls.showZ = !hideZ;
};

// Derive the plane's normal from the helper's current quaternion and push it
// into the stored normal and THREE.Plane math. Also updates gizmo ring visibility.
// OBC's Object3D.lookAt(normal) makes local +Z point along the normal direction.
const syncNormalFromHelper = (plane: OBC.SimplePlane) => {
  const helper = (plane as any)._helper as THREE.Object3D | undefined;
  if (!helper) return;
  const controls = (plane as any)._controls;
  const newNormal = new THREE.Vector3(0, 0, 1)
    .applyQuaternion(helper.quaternion)
    .normalize();
  (plane as any).normal.copy(newNormal);
  (plane as any).update();
  if (controls) updateRingVisibility(controls, newNormal);
};

const enablePlaneRotate = (key: string, plane: OBC.SimplePlane) => {
  if (_rotateListeners.has(key)) return;
  const controls = (plane as any)._controls;
  if (!controls) return;
  controls.setSpace("world");
  controls.mode = "rotate";
  updateRingVisibility(controls, (plane as any).normal as THREE.Vector3);
  const listener = () => syncNormalFromHelper(plane);
  (controls as any).addEventListener("change", listener);
  _rotateListeners.set(key, listener);

  // OBC's changeDrag sets _visible=false when drag starts, which causes downstream
  // code to hide the plane mesh. Counter it: after changeDrag runs, restore visibility.
  const dragPreserver = (e: any) => {
    if (e.value) {
      (plane as any)._visible = true;
      (plane as any)._helper.visible = true;
      controls.getHelper().visible = true;
    }
  };
  (controls as any).addEventListener("dragging-changed", dragPreserver);
  _dragPreservers.set(key, dragPreserver);

  // Setting controls.mode/showX/etc fires TransformControls "change" events which
  // can trigger OBC internals that hide the helper mesh. Restore visibility after
  // all property changes have settled.
  requestAnimationFrame(() => {
    (plane as any)._visible = true;
    (plane as any)._helper.visible = true;
    controls.getHelper().visible = true;
  });
};

const disablePlaneRotate = (key: string, plane: OBC.SimplePlane) => {
  const controls = (plane as any)._controls;
  if (!controls) return;
  const listener = _rotateListeners.get(key);
  if (listener) {
    (controls as any).removeEventListener("change", listener);
    _rotateListeners.delete(key);
  }
  const dragPreserver = _dragPreservers.get(key);
  if (dragPreserver) {
    (controls as any).removeEventListener("dragging-changed", dragPreserver);
    _dragPreservers.delete(key);
  }
  controls.mode = "translate";
  controls.showX = false;
  controls.showY = false;
  controls.showZ = true;
  controls.setSpace("local");
};

const applyModeToAllPlanes = (clipper: OBC.Clipper, mode: SectionMode) => {
  for (const [key, plane] of clipper.list) {
    mode === "rotate" ? enablePlaneRotate(key, plane) : disablePlaneRotate(key, plane);
  }
};

// ── Template ──────────────────────────────────────────────────────────────────
export const sectionPanelTemplate: BUI.StatefullComponent<SectionPanelState> = (
  state,
  update,
) => {
  const { components, world } = state;
  const clipper = components.get(OBC.Clipper);
  const highlighter = components.get(OBF.Highlighter);

  _bimUpdate = update;

  if (!state._listenersSet) {
    state._listenersSet = true;

    clipper.list.onItemSet.add(({ key, value: plane }) => {
      console.log("[PNT] section plane added | total:", clipper.list.size);
      if (!_originalNormals.has(key)) {
        _originalNormals.set(key, (plane as any).normal.clone());
      }
      if (_currentMode === "rotate") enablePlaneRotate(key, plane);
      update();
    });
    clipper.list.onItemDeleted.add((key: string) => {
      console.log("[PNT] section plane deleted | total:", clipper.list.size);
      _rotateListeners.delete(key);
      _originalNormals.delete(key);
      update();
    });

    window.addEventListener(TOGGLE_SECTION_PANEL, () => {
      sectionPanelVisible = !sectionPanelVisible;
      clipper.enabled = sectionPanelVisible;
      highlighter.enabled = !sectionPanelVisible;
      if (!sectionPanelVisible) applyModeToAllPlanes(clipper, "translate");
      console.log("[PNT] section panel visible:", sectionPanelVisible);
      if (_bimUpdate) _bimUpdate();
    });

    window.addEventListener(TOGGLE_SECTION_MODE, () => {
      _currentMode = _currentMode === "translate" ? "rotate" : "translate";
      applyModeToAllPlanes(clipper, _currentMode);
      console.log("[PNT] section mode →", _currentMode);
      if (_bimUpdate) _bimUpdate({ mode: _currentMode });
    });
  }

  const planes = [...clipper.list];
  const hasPlanes = planes.length > 0;

  const onDeleteAll = () => {
    console.log("[PNT] delete all planes:", clipper.list.size);
    clipper.deleteAll();
    update();
  };

  const onToggleMode = () => {
    _currentMode = state.mode === "translate" ? "rotate" : "translate";
    applyModeToAllPlanes(clipper, _currentMode);
    update({ mode: _currentMode });
  };

  const onResetPlane = (key: string, plane: OBC.SimplePlane) => {
    const orig = _originalNormals.get(key);
    if (!orig) return;
    const currentPos = (plane as any)._helper.position.clone() as THREE.Vector3;
    plane.setFromNormalAndCoplanarPoint(orig.clone(), currentPos);
    if (_currentMode === "rotate") {
      const ctrl = (plane as any)._controls;
      if (ctrl) updateRingVisibility(ctrl, orig);
    }
    components.get(OBC.FragmentsManager).core.update(true);
    update();
  };

  const rowStyle = "display:flex; align-items:center; gap:0.25rem; padding:0.1rem 0.5rem";
  const iconBtnStyle = "flex:0 0 auto; --bim-button--bgc:transparent; --bim-button--p:0.15rem 0.3rem; --bim-icon-size:0.75rem";

  const planeRows = planes.map(([key, plane], i) => BUI.html`
    <div style=${rowStyle}>
      <bim-button
        style="flex:1; min-width:0; --bim-button--bgc:transparent; --bim-button--p:0.15rem 0"
        label="Plane ${i + 1}"
        icon=${plane.enabled ? "mdi:eye" : "mdi:eye-off"}
        ?active=${plane.enabled}
        @click=${() => { plane.enabled = !plane.enabled; update(); }}
      ></bim-button>
      <bim-button
        icon=${plane.visible ? "mdi:lightbulb" : "mdi:lightbulb-off-outline"}
        style=${iconBtnStyle}
        tooltip-title="Show/hide plane visual (keeps section active)"
        ?disabled=${!plane.enabled}
        @click=${() => { plane.visible = !plane.visible; update(); }}
      ></bim-button>
      <bim-button
        icon="mdi:restore"
        style=${iconBtnStyle}
        tooltip-title="Reset rotation"
        @click=${() => onResetPlane(key, plane)}
      ></bim-button>
      <bim-button
        icon="mdi:trash-can-outline"
        style=${iconBtnStyle}
        @click=${async () => { await clipper.delete(world, key); update(); }}
      ></bim-button>
    </div>
  `);

  const labelStyle = "white-space: normal; word-break: break-word; font-size:0.7rem; opacity:0.6";

  return BUI.html`
    <bim-panel
      label="Section"
      style="
        position: absolute;
        top: 0.5rem;
        bottom: 7rem;
        left: 0.5rem;
        width: 14rem;
        overflow-y: auto;
        pointer-events: all;
        z-index: 10;
      "
      ?hidden=${!sectionPanelVisible}
    >
      <bim-panel-section label="Mode">
        <bim-button
          label=${state.mode === "translate" ? "Move" : "Tilt"}
          icon=${state.mode === "translate" ? "mdi:cursor-move" : "mdi:rotate-3d"}
          ?active=${state.mode === "rotate"}
          @click=${onToggleMode}
        ></bim-button>
        <bim-label style=${labelStyle}>In Tilt mode: drag the rotation rings in the viewport to change the plane angle.</bim-label>
      </bim-panel-section>

      ${hasPlanes ? BUI.html`
        <bim-panel-section label="Planes">
          ${planeRows}
          <div style="padding:0.25rem 0.5rem">
            <bim-button label="Delete All" @click=${onDeleteAll}></bim-button>
          </div>
        </bim-panel-section>
      ` : BUI.html`
        <bim-panel-section>
          <bim-label style=${labelStyle}>No section planes yet. Double-click the model to create one.</bim-label>
        </bim-panel-section>
      `}
    </bim-panel>
  `;
};
