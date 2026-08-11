<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform -->

# Copilot Instructions

This agent acts as a complement to Claude in this repository.

## Precedence

- `CLAUDE.md` is the canonical authority for project-specific AI guidance.
- If there is any conflict between this file and `CLAUDE.md`, `CLAUDE.md` takes precedence.
- Do not create a second source of truth for PyNET, Navisworks, or project workflow rules that already exist in `CLAUDE.md`.

## Copilot Role

- Suggest completions and edits consistent with the PyNET platform conventions.
- Review code and flag risks or regressions before they reach the bridge.
- Help with repository maintenance, automation, and focused technical tasks.
- Reuse the project context and workflow already defined for Claude instead of redefining it.

## Boundaries

- Keep project rules, domain workflow, execution constraints, and approval policy in `CLAUDE.md`.
- Use this file only for Copilot-specific working notes or lightweight behavioral guidance.
- Prefer referencing existing guidance over duplicating it.

## Key Platform Facts

- Scripts run inside **Navisworks**, **Revit**, or **AutoCAD / Civil 3D** via **Python.NET** (CPython 3.10).
- The MCP bridge is `pynet-mcp-bridge` (not `pynet-bridge`). Current version: **1.4.10**.
- Use `pathlib.Path` — never `os.path`.
- Clash helper utilities live in `01_Scripts/00_utils/pynet_clash.py` (`get_clash_tests`, `iter_results`).
- The Navisworks Clash API changed in 2026/2027: never call `.Tests` directly — always use `get_clash_tests()`.
- Output structured data via `ia_Result` (list of dicts); keep `print` minimal during development.
- Security validator blocks: `os`, `subprocess`, `shutil`, `socket`, `glob`, `inspect`, `eval`, `exec`.

## Language Policy

- All internal agent configuration, skills, command files, and persistent AI documentation must be written in English.
- User-facing conversation should match the user's language.
- If the user writes in Spanish, reply in Spanish.
- If the user writes in English, reply in English.
- In case of doubt, keep persistent repository AI artifacts in English.
