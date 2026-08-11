<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform -->

# Guide: UI management & button deployment (Navisworks)

Read this guide when **creating modules, deploying buttons, or controlling the Output Window** via MCP.

---

## UI inspection

- `get_pynet_ui_layout` — full UI structure. Use it to get `Id` values before updating/deleting elements.

## Creation & deployment

| Action | MCP tool | Main input |
|---|---|---|
| Create module | `create_pynet_module` | new module name |
| Deploy button | `deploy_script_button` | `module_id`, script path, name, icon |

> **CRITICAL — always use ABSOLUTE paths** for `script_Path` in `deploy_script_button` and `update_script_button`. Relative paths save silently but fail at runtime with "Script File not found". Example: `C:\Repos\PyNetLibrary\01_Scripts\...`

## Editing & cleanup

- `update_script_button` — change name, icon, tooltip.
- `delete_script_button` — remove a button.
- `delete_pynet_module` — remove a module and all its buttons.

## Icons

Use predefined icon names (e.g. `Gear`, `Python`, `Database`, `Search`, `Eye`, `ChartBar`, `ShieldSearch`). Full catalog: `00_References/iconsMin.txt`. Default icon is assigned if none specified.

---

## Output Window

The Navisworks plugin has a visible Output Window showing every `print()` in real time.

- `configure_output_window(pid, is_available=True/False)` — toggle visibility, useful for debugging.

See `CLAUDE.md` for the `print` vs `ia_Result` policy (quiet prints during development, informative prints in saved scripts).
