// SPDX-License-Identifier: MIT
// Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import * as BUI from "@thatopen/ui";
import * as OBC from "@thatopen/components";
import * as OBF from "@thatopen/components-front";
import * as FRAGS from "@thatopen/fragments";
import * as THREE from "three";
import { appIcons, tooltips } from "../../globals";
import { TOGGLE_MEASUREMENTS_PANEL, measurementsPanelVisible } from "../panels/measurements-panel";
import { TOGGLE_SECTION_PANEL, sectionPanelVisible } from "../panels/section-panel";
import { TOGGLE_PROPERTIES_PANEL, propertiesPanelVisible } from "../panels/properties-panel";
import { TOGGLE_TREE_PANEL, treePanelVisible } from "../panels/spatial-tree-panel";

// Styles a clash pair (or any element set) is highlighted under. Focus / Hide / Isolate must
// consider these too — a picked clash lives in "clash-a"/"clash-b", not the click "select" style.
const SELECTION_STYLES = ["select", "clash-a", "clash-b"];

// Merge every active highlight style into a single ModelIdMap so visibility/camera actions
// operate on whatever is currently marked, regardless of which style painted it.
const getActiveSelection = (highlighter: OBF.Highlighter): OBC.ModelIdMap => {
  const merged: OBC.ModelIdMap = {};
  for (const name of SELECTION_STYLES) {
    const sel = (highlighter.selection as Record<string, OBC.ModelIdMap>)[name];
    if (!sel) continue;
    for (const [modelId, ids] of Object.entries(sel)) {
      if (!merged[modelId]) merged[modelId] = new Set<number>();
      for (const id of ids as Set<number>) (merged[modelId] as Set<number>).add(id);
    }
  }
  return merged;
};

export interface ViewerToolbarState {
  components: OBC.Components;
  world: OBC.World;
}

const originalColors = new Map<
  FRAGS.BIMMaterial,
  { color: number; transparent: boolean; opacity: number }
>();

const setModelTransparent = (components: OBC.Components) => {
  const fragments = components.get(OBC.FragmentsManager);

  const materials = [...fragments.core.models.materials.list.values()];
  for (const material of materials) {
    if (material.userData.customId) continue;
    let color: number | undefined;
    if ("color" in material) {
      color = material.color.getHex();
    } else {
      color = material.lodColor.getHex();
    }

    originalColors.set(material, {
      color,
      transparent: material.transparent,
      opacity: material.opacity,
    });

    material.transparent = true;
    material.opacity = 0.05;
    material.needsUpdate = true;
    if ("color" in material) {
      material.color.setColorName("white");
    } else {
      material.lodColor.setColorName("white");
    }
  }
};

const restoreModelMaterials = () => {
  for (const [material, data] of originalColors) {
    const { color, transparent, opacity } = data;
    material.transparent = transparent;
    material.opacity = opacity;
    if ("color" in material) {
      material.color.setHex(color);
    } else {
      material.lodColor.setHex(color);
    }
    material.needsUpdate = true;
  }
  originalColors.clear();
};

export const viewerToolbarTemplate: BUI.StatefullComponent<
  ViewerToolbarState
> = (state, update) => {
  const { components, world } = state;

  const highlighter = components.get(OBF.Highlighter);
  const hider = components.get(OBC.Hider);
  const lengthMeasurer = components.get(OBF.LengthMeasurement);
  const areaMeasurer = components.get(OBF.AreaMeasurement);

  const onToggleMeasurements = () => {
    window.dispatchEvent(new Event(TOGGLE_MEASUREMENTS_PANEL));
    requestAnimationFrame(() => update());
  };

  const onToggleSection = () => {
    BUI.ContextMenu.removeMenus();
    highlighter.clear("select");
    lengthMeasurer.enabled = false;
    areaMeasurer.enabled = false;
    if (measurementsPanelVisible) window.dispatchEvent(new Event(TOGGLE_MEASUREMENTS_PANEL));
    window.dispatchEvent(new Event(TOGGLE_SECTION_PANEL));
    requestAnimationFrame(() => update());
  };

  const onToggleProperties = () => {
    window.dispatchEvent(new Event(TOGGLE_PROPERTIES_PANEL));
    requestAnimationFrame(() => update());
  };

  const measurementsActive = measurementsPanelVisible || lengthMeasurer.enabled || areaMeasurer.enabled;

  const onToggleGhost = () => {
    if (originalColors.size) {
      restoreModelMaterials();
    } else {
      setModelTransparent(components);
    }
  };

  let focusBtn: BUI.TemplateResult | undefined;
  if (world.camera instanceof OBC.SimpleCamera) {
    const onFocus = async ({ target }: { target: BUI.Button }) => {
      if (!(world.camera instanceof OBC.SimpleCamera)) return;
      const selection = getActiveSelection(highlighter);
      target.loading = true;
      await world.camera.fitToItems(
        OBC.ModelIdMapUtils.isEmpty(selection) ? undefined : selection,
      );
      target.loading = false;
    };

    focusBtn = BUI.html`<bim-button tooltip-title=${tooltips.FOCUS.TITLE} tooltip-text=${tooltips.FOCUS.TEXT} icon=${appIcons.FOCUS} label="Focus" @click=${onFocus}></bim-button>`;
  }

  const onHide = async ({ target }: { target: BUI.Button }) => {
    const selection = getActiveSelection(highlighter);
    if (OBC.ModelIdMapUtils.isEmpty(selection)) return;
    target.loading = true;
    await hider.set(false, selection);
    target.loading = false;
  };

  const onIsolate = async ({ target }: { target: BUI.Button }) => {
    const selection = getActiveSelection(highlighter);
    if (OBC.ModelIdMapUtils.isEmpty(selection)) return;
    target.loading = true;
    await hider.isolate(selection);
    target.loading = false;
  };

  const onToggleTree = () => {
    window.dispatchEvent(new Event(TOGGLE_TREE_PANEL));
    requestAnimationFrame(() => update());
  };

  const onShowAll = async ({ target }: { target: BUI.Button }) => {
    target.loading = true;
    await hider.set(true);
    target.loading = false;
  };

  const onResetVisibility = async ({ target }: { target: BUI.Button }) => {
    target.loading = true;
    // Restore toolbar ghost (if Toggle Ghost was used)
    if (originalColors.size) restoreModelMaterials();
    // Restore clash ghost + clear clash highlights (_savedMats in main.ts).
    // highlightClash(null,null) does _restoreAll() but exits before core.update,
    // so we must call update ourselves below.
    if (typeof (window as any).highlightClash === "function") {
      await (window as any).highlightClash(null, null);
    }
    // Show all hidden / isolated elements
    await hider.set(true);
    // Force render pass so material changes are visible
    await components.get(OBC.FragmentsManager).core.update(true);
    target.loading = false;
  };

  const colorInputId = BUI.Manager.newRandomId();
  const getColorValue = () => {
    const input = document.getElementById(
      colorInputId,
    ) as BUI.ColorInput | null;
    if (!input) return null;
    return input.color;
  };

  const onApplyColor = async ({ target }: { target: BUI.Button }) => {
    const colorValue = getColorValue();
    const selection = highlighter.selection.select;
    if (OBC.ModelIdMapUtils.isEmpty(selection) || !colorValue) return;
    const color = new THREE.Color(colorValue);
    const style = [...highlighter.styles.entries()].find(([, definition]) => {
      if (!definition) return false;
      return definition.color.getHex() === color.getHex();
    });
    target.loading = true;
    if (style) {
      const name = style[0];
      if (name === "select") {
        target.loading = false;
        return;
      }
      await highlighter.highlightByID(name, selection, false, false);
    } else {
      highlighter.styles.set(colorValue, {
        color,
        renderedFaces: FRAGS.RenderedFaces.ONE,
        opacity: 1,
        transparent: false,
      });
      await highlighter.highlightByID(colorValue, selection, false, false);
    }
    await highlighter.clear("select");
    target.loading = false;
  };

  return BUI.html`
    <bim-toolbar>
      <bim-toolbar-section label="Tools" icon=${appIcons.TOOLS}>
        <bim-button
          ?active=${measurementsActive}
          label="Measurements"
          icon=${appIcons.RULER}
          tooltip-title="Measurements Panel"
          tooltip-text="Open the measurements panel to measure lengths and areas."
          @click=${onToggleMeasurements}
        ></bim-button>
        <bim-button
          ?active=${sectionPanelVisible}
          label="Section"
          icon=${appIcons.CLIPPING}
          tooltip-title="Section Planes"
          tooltip-text="Open the section panel to create and manage clipping planes."
          @click=${onToggleSection}
        ></bim-button>
        <bim-button
          ?active=${propertiesPanelVisible}
          label="Properties"
          icon=${appIcons.PROPERTIES}
          tooltip-title="Element Properties"
          tooltip-text="Open the properties panel. Select an element to see its IFC data."
          @click=${onToggleProperties}
        ></bim-button>
        <bim-button
          ?active=${treePanelVisible}
          label="Models Tree"
          icon=${appIcons.TREE}
          tooltip-title=${tooltips.TREE.TITLE}
          tooltip-text=${tooltips.TREE.TEXT}
          @click=${onToggleTree}
        ></bim-button>
      </bim-toolbar-section>
      <bim-toolbar-section label="Visibility" icon=${appIcons.SHOW}>
        <bim-button tooltip-title=${tooltips.SHOW_ALL.TITLE} tooltip-text=${tooltips.SHOW_ALL.TEXT} icon=${appIcons.SHOW} label="Show All" @click=${onShowAll}></bim-button>
        <bim-button tooltip-title=${tooltips.GHOST.TITLE} tooltip-text=${tooltips.GHOST.TEXT} icon=${appIcons.TRANSPARENT} label="Toggle Ghost" @click=${onToggleGhost}></bim-button>
        <bim-button icon="mdi:restore" label="Reset Visibility" tooltip-title="Reset Visibility" tooltip-text="Restore all visibility changes: show hidden elements and remove ghost mode." @click=${onResetVisibility}></bim-button>
      </bim-toolbar-section>
      <bim-toolbar-section label="Selection" icon=${appIcons.SELECT}>
        ${focusBtn}
        <bim-button tooltip-title=${tooltips.HIDE.TITLE} tooltip-text=${tooltips.HIDE.TEXT} icon=${appIcons.HIDE} label="Hide" @click=${onHide}></bim-button>
        <bim-button tooltip-title=${tooltips.ISOLATE.TITLE} tooltip-text=${tooltips.ISOLATE.TEXT} icon=${appIcons.ISOLATE} label="Isolate" @click=${onIsolate}></bim-button>
        <bim-button icon=${appIcons.COLORIZE} label="Colorize">
          <bim-context-menu>
            <div style="display: flex; gap: 0.5rem; width: 10rem;">
              <bim-color-input id=${colorInputId}></bim-color-input>
              <bim-button label="Apply" @click=${onApplyColor}></bim-button>
            </div>
          </bim-context-menu>
        </bim-button>
      </bim-toolbar-section>
    </bim-toolbar>
  `;
};
