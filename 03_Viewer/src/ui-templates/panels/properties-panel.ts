// SPDX-License-Identifier: MIT
// Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform

import * as BUI from "@thatopen/ui";

export const TOGGLE_PROPERTIES_PANEL = "toggle-properties-panel";
export const PROPERTIES_DATA_EVENT = "properties-data";
export let propertiesPanelVisible = false;

export interface PropertiesData {
  pnt_id: string;
  name: string;
  model: string;
  psets: Record<string, Record<string, unknown>>;
}

const ELEMENT_KEY = "__element__";

let _currentData: PropertiesData | null = null;
let _selectedPSet: string = ELEMENT_KEY;
let _dropdownOpen = false;
let _bimUpdate: BUI.UpdateFunction<PropertiesPanelState> | null = null;

let _scrollbarStyled = false;
const _ensureScrollbarStyle = () => {
  if (_scrollbarStyled) return;
  _scrollbarStyled = true;
  const s = document.createElement("style");
  s.textContent = [
    `*::-webkit-scrollbar{width:5px;height:5px}`,
    `*::-webkit-scrollbar-track{background:transparent}`,
    `*::-webkit-scrollbar-thumb{background:rgba(67,136,177,.55);border-radius:3px}`,
    `*::-webkit-scrollbar-thumb:hover{background:rgba(67,136,177,.85)}`,
    `.pnt-opt:hover{background:rgba(67,136,177,0.2)!important}`,
  ].join(" ");
  document.head.appendChild(s);
};

interface PropertiesPanelState {
  _listenersSet?: boolean;
}

export const propertiesPanelTemplate: BUI.StatefullComponent<PropertiesPanelState> = (
  state,
  update,
) => {
  _bimUpdate = update;
  _ensureScrollbarStyle();

  if (!state._listenersSet) {
    state._listenersSet = true;

    window.addEventListener("click", () => {
      if (_dropdownOpen) {
        _dropdownOpen = false;
        if (_bimUpdate) _bimUpdate();
      }
    });

    window.addEventListener(TOGGLE_PROPERTIES_PANEL, () => {
      propertiesPanelVisible = !propertiesPanelVisible;
      console.log("[PNT] properties panel visible:", propertiesPanelVisible);
      if (_bimUpdate) _bimUpdate();
    });

    window.addEventListener(PROPERTIES_DATA_EVENT, (e: Event) => {
      const data = (e as CustomEvent<PropertiesData | null>).detail;
      _currentData = data;
      if (data) {
        const keys = Object.keys(data.psets);
        // Keep current selection if it exists, otherwise reset to Element
        if (_selectedPSet !== ELEMENT_KEY && !keys.includes(_selectedPSet))
          _selectedPSet = ELEMENT_KEY;
      } else {
        _selectedPSet = ELEMENT_KEY;
      }
      console.log("[PNT] properties data:", data?.name ?? "null", "| pset:", _selectedPSet);
      if (propertiesPanelVisible && _bimUpdate) _bimUpdate();
    });
  }

  const data = _currentData;
  const hintStyle = "white-space:normal; word-break:break-word; font-size:0.7rem; opacity:0.6";
  const rowStyle = "display:flex; gap:0.5rem; padding:0.3rem 0; border-bottom:1px solid rgba(255,255,255,0.05); align-items:flex-start";
  const keyStyle = "flex:0 0 42%; min-width:0; font-size:0.72rem; opacity:0.55; white-space:normal; word-break:break-word; overflow-wrap:anywhere";
  const valStyle = "flex:1; min-width:0; font-size:0.75rem; white-space:normal; word-break:break-word; overflow-wrap:anywhere";

  const currentLabel = _selectedPSet === ELEMENT_KEY ? "Element" : _selectedPSet;

  const toggleDropdown = (e: Event) => {
    e.stopPropagation();
    _dropdownOpen = !_dropdownOpen;
    if (_bimUpdate) _bimUpdate();
  };

  const onOptionClick = (e: Event, value: string) => {
    e.stopPropagation();
    _selectedPSet = value;
    _dropdownOpen = false;
    console.log("[PNT] pset selected:", _selectedPSet);
    if (_bimUpdate) _bimUpdate();
  };

  const triggerStyle = [
    "display:flex", "justify-content:space-between", "align-items:center",
    "background:#1c1c24", "color:#d0d0d0",
    `border:1px solid ${_dropdownOpen ? "rgba(67,136,177,0.8)" : "rgba(67,136,177,0.4)"}`,
    `border-radius:${_dropdownOpen ? "4px 4px 0 0" : "4px"}`,
    "padding:0.38rem 0.5rem",
    "font-size:0.8rem", "cursor:pointer", "user-select:none", "box-sizing:border-box",
  ].join(";");

  const listStyle = [
    "background:#1c1c24", "border:1px solid rgba(67,136,177,0.6)", "border-top:none",
    "border-radius:0 0 4px 4px", "max-height:180px", "overflow-y:auto",
    "scrollbar-width:thin", "scrollbar-color:rgba(67,136,177,.55) transparent",
  ].join(";");

  const optStyle = (active: boolean) =>
    `padding:0.35rem 0.5rem; cursor:pointer; font-size:0.8rem; color:#d0d0d0;` +
    (active ? "background:rgba(67,136,177,0.3);" : "");

  const psetNames = data ? Object.keys(data.psets) : [];

  const rows: [string, string][] = !data ? [] :
    _selectedPSet === ELEMENT_KEY
      ? [["Name", data.name], ["Model", data.model]]
      : Object.entries(data.psets[_selectedPSet] ?? {}).map(([k, v]) => [k, String(v)]);

  return BUI.html`
    <bim-panel
      label="Properties"
      style="
        position: absolute;
        top: 0.5rem;
        bottom: 7rem;
        left: 0.5rem;
        width: 18rem;
        pointer-events: all;
        z-index: 10;
      "
      ?hidden=${!propertiesPanelVisible}
    >
      ${!data ? BUI.html`
        <bim-panel-section>
          <bim-label style=${hintStyle}>Select an element in the viewport to see its properties.</bim-label>
        </bim-panel-section>
      ` : BUI.html`
        <bim-panel-section label="Property Sets">

          <div style=${triggerStyle} @click=${toggleDropdown}>
            <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1">${currentLabel}</span>
            <span style="margin-left:0.4rem;font-size:0.55rem;opacity:0.65;flex-shrink:0">${_dropdownOpen ? "▲" : "▼"}</span>
          </div>

          ${_dropdownOpen ? BUI.html`
            <div style=${listStyle}>
              <div class="pnt-opt" style=${optStyle(_selectedPSet === ELEMENT_KEY)}
                @click=${(e: Event) => onOptionClick(e, ELEMENT_KEY)}>Element</div>
              ${psetNames.map(name => BUI.html`
                <div class="pnt-opt" style=${optStyle(name === _selectedPSet)}
                  @click=${(e: Event) => onOptionClick(e, name)}>${name}</div>
              `)}
            </div>
          ` : BUI.html``}

          <div style="overflow-y:auto; max-height:calc(100vh - 18rem); margin-top:0.25rem; padding-right:0.3rem;">
            ${rows.map(([k, v]) => BUI.html`
              <div style=${rowStyle}>
                <bim-label style=${keyStyle} title=${k}>${k}</bim-label>
                <bim-label style=${valStyle} title=${v}>${v}</bim-label>
              </div>
            `)}
          </div>

        </bim-panel-section>
      `}
    </bim-panel>
  `;
};
