import * as BUI from "@thatopen/ui";
import * as OBC from "@thatopen/components";
import * as OBF from "@thatopen/components-front";
import { appIcons } from "../../globals";

export const TOGGLE_MEASUREMENTS_PANEL = "toggle-measurements-panel";
export let measurementsPanelVisible = false;

type LengthUnit = "m" | "cm" | "mm" | "km";
type AreaUnit = "m2" | "cm2" | "mm2" | "km2";

interface MeasurementsPanelState {
  components: OBC.Components;
  lengthUnit: LengthUnit;
  areaUnit: AreaUnit;
  _listenersSet?: boolean;
}

// Raw-value converters — panel computes independently of line.units internal state
const convertLength = (meters: number, unit: LengthUnit): number => {
  switch (unit) {
    case "cm": return meters * 100;
    case "mm": return meters * 1000;
    case "km": return meters / 1000;
    default:   return meters;
  }
};

const convertArea = (m2: number, unit: AreaUnit): number => {
  switch (unit) {
    case "cm2": return m2 * 10000;
    case "mm2": return m2 * 1000000;
    case "km2": return m2 / 1000000;
    default:    return m2;
  }
};

export const measurementsPanelTemplate: BUI.StatefullComponent<MeasurementsPanelState> = (
  state,
  update,
) => {
  const { components } = state;
  const lengthMeasurer = components.get(OBF.LengthMeasurement);
  const areaMeasurer = components.get(OBF.AreaMeasurement);
  const highlighter = components.get(OBF.Highlighter);
  const clipper = components.get(OBC.Clipper);

  if (!state._listenersSet) {
    state._listenersSet = true;

    lengthMeasurer.list.onItemAdded.add((line) => {
      console.log("[PNT] length added, raw:", line.distance().toFixed(3), "m | total:", lengthMeasurer.list.size);
      update();
    });
    lengthMeasurer.list.onItemDeleted.add(() => {
      console.log("[PNT] length deleted | total:", lengthMeasurer.list.size);
      update();
    });
    areaMeasurer.list.onItemAdded.add((area) => {
      console.log("[PNT] area added, raw:", area.rawValue.toFixed(3), "m2 | total:", areaMeasurer.list.size);
      update();
    });
    areaMeasurer.list.onItemDeleted.add(() => {
      console.log("[PNT] area deleted | total:", areaMeasurer.list.size);
      update();
    });

    window.addEventListener(TOGGLE_MEASUREMENTS_PANEL, () => {
      measurementsPanelVisible = !measurementsPanelVisible;
      console.log("[PNT] measurements panel visible:", measurementsPanelVisible);
      update();
    });
  }

  // ── Mode switching ────────────────────────────────────────────────────────
  const disableAllTools = () => {
    lengthMeasurer.enabled = false;
    areaMeasurer.enabled = false;
    clipper.enabled = false;
    highlighter.enabled = true;
  };

  const onLengthMode = () => {
    if (lengthMeasurer.enabled) {
      lengthMeasurer.enabled = false;
      highlighter.enabled = true;
    } else {
      disableAllTools();
      (lengthMeasurer as any).units = state.lengthUnit;
      lengthMeasurer.enabled = true;
      highlighter.enabled = false;
    }
    console.log("[PNT] length mode:", lengthMeasurer.enabled);
    update();
  };

  const onAreaMode = () => {
    if (areaMeasurer.enabled) {
      areaMeasurer.enabled = false;
      highlighter.enabled = true;
    } else {
      disableAllTools();
      (areaMeasurer as any).units = state.areaUnit;
      areaMeasurer.enabled = true;
      highlighter.enabled = false;
    }
    console.log("[PNT] area mode:", areaMeasurer.enabled);
    update();
  };

  // ── Units ─────────────────────────────────────────────────────────────────
  const applyLengthUnits = (u: LengthUnit) => {
    state.lengthUnit = u;
    (lengthMeasurer as any).units = u; // updates 3D labels
    console.log("[PNT] length units →", u);
    update();
  };

  const applyAreaUnits = (u: AreaUnit) => {
    state.areaUnit = u;
    (areaMeasurer as any).units = u;
    console.log("[PNT] area units →", u);
    update();
  };

  const onLengthUnits = ({ target }: { target: BUI.Dropdown }) => {
    const [unit] = target.value;
    if (unit) applyLengthUnits(unit as LengthUnit);
  };

  const onAreaUnits = ({ target }: { target: BUI.Dropdown }) => {
    const [unit] = target.value;
    if (unit) applyAreaUnits(unit as AreaUnit);
  };

  // ── Delete / clear ────────────────────────────────────────────────────────
  const onDeleteLength = (line: OBF.Line) => {
    console.log("[PNT] delete length | before:", lengthMeasurer.list.size);
    lengthMeasurer.list.delete(line);
    update();
  };

  const onDeleteArea = (area: OBF.Area) => {
    console.log("[PNT] delete area | before:", areaMeasurer.list.size);
    areaMeasurer.list.delete(area);
    update();
  };

  const onClearLength = () => {
    console.log("[PNT] clear length:", lengthMeasurer.list.size);
    lengthMeasurer.list.clear();
    update();
  };

  const onClearArea = () => {
    console.log("[PNT] clear area:", areaMeasurer.list.size);
    areaMeasurer.list.clear();
    update();
  };

  const onClearAll = () => {
    onClearLength();
    onClearArea();
  };

  // ── Render data ───────────────────────────────────────────────────────────
  const lengthItems = [...lengthMeasurer.list];
  const areaItems = [...areaMeasurer.list];
  const hasItems = lengthItems.length > 0 || areaItems.length > 0;

  // Panel reads from raw values and converts with state unit — independent of line.units internals
  const rowStyle = "display:flex; align-items:center; gap:0.25rem; padding:0.1rem 0.5rem";
  const trashStyle = "flex:0 0 20%; --bim-button--bgc:transparent; --bim-button--p:0.15rem 0; --bim-icon-size:0.75rem";

  const lengthListItems = lengthItems.map((line) => {
    const val = convertLength(line.distance(), state.lengthUnit).toFixed(2);
    return BUI.html`
      <div style=${rowStyle}>
        <bim-label style="flex:0 0 80%; min-width:0">${val} ${state.lengthUnit}</bim-label>
        <bim-button icon="mdi:trash-can-outline" style=${trashStyle} @click=${() => onDeleteLength(line)}></bim-button>
      </div>
    `;
  });

  const areaListItems = areaItems.map((area) => {
    const val = convertArea(area.rawValue, state.areaUnit).toFixed(2);
    return BUI.html`
      <div style=${rowStyle}>
        <bim-label style="flex:1; min-width:0">${val} ${state.areaUnit}</bim-label>
        <bim-button icon="mdi:trash-can-outline" style=${trashStyle} @click=${() => onDeleteArea(area)}></bim-button>
      </div>
    `;
  });

  return BUI.html`
    <bim-panel
      label="Measurements"
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
      ?hidden=${!measurementsPanelVisible}
    >
      <!-- Mode + Units -->
      <bim-panel-section label="Mode">
        <div style="display:flex; gap:0.5rem">
          <bim-button
            style="flex:1"
            ?active=${lengthMeasurer.enabled}
            label="Length"
            icon=${appIcons.RULER}
            @click=${onLengthMode}
          ></bim-button>
          <bim-button
            style="flex:1"
            ?active=${areaMeasurer.enabled}
            label="Area"
            icon="ph:polygon"
            @click=${onAreaMode}
          ></bim-button>
        </div>

        ${lengthMeasurer.enabled ? BUI.html`
          <bim-dropdown label="Units" @change=${onLengthUnits}>
            <bim-option label="m"  ?checked=${state.lengthUnit === "m"}></bim-option>
            <bim-option label="cm" ?checked=${state.lengthUnit === "cm"}></bim-option>
            <bim-option label="mm" ?checked=${state.lengthUnit === "mm"}></bim-option>
            <bim-option label="km" ?checked=${state.lengthUnit === "km"}></bim-option>
          </bim-dropdown>
        ` : BUI.html``}

        ${areaMeasurer.enabled ? BUI.html`
          <bim-dropdown label="Units" @change=${onAreaUnits}>
            <bim-option label="m2"  ?checked=${state.areaUnit === "m2"}></bim-option>
            <bim-option label="cm2" ?checked=${state.areaUnit === "cm2"}></bim-option>
            <bim-option label="mm2" ?checked=${state.areaUnit === "mm2"}></bim-option>
            <bim-option label="km2" ?checked=${state.areaUnit === "km2"}></bim-option>
          </bim-dropdown>
        ` : BUI.html``}
      </bim-panel-section>

      <!-- Length list -->
      ${lengthListItems.length > 0 ? BUI.html`
        <bim-panel-section label="Length" icon=${appIcons.RULER}>
          ${lengthListItems}
          <div style="padding:0.25rem 0.5rem">
            <bim-button label="Clear" @click=${onClearLength}></bim-button>
          </div>
        </bim-panel-section>
      ` : BUI.html``}

      <!-- Area list -->
      ${areaListItems.length > 0 ? BUI.html`
        <bim-panel-section label="Area" icon="ph:polygon">
          ${areaListItems}
          <div style="padding:0.25rem 0.5rem">
            <bim-button label="Clear" @click=${onClearArea}></bim-button>
          </div>
        </bim-panel-section>
      ` : BUI.html``}

      <!-- Empty state -->
      ${!hasItems ? BUI.html`
        <bim-panel-section>
          <bim-label style="white-space:normal; word-break:break-word">No measurements yet. Enable Length or Area above and double-click in the scene.</bim-label>
        </bim-panel-section>
      ` : BUI.html``}

      <!-- Clear all -->
      ${hasItems ? BUI.html`
        <div style="padding:0.25rem 0.5rem 0.5rem">
          <bim-button label="Clear All" @click=${onClearAll}></bim-button>
        </div>
      ` : BUI.html``}
    </bim-panel>
  `;
};
