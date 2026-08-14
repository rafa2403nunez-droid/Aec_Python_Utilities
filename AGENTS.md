<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform -->

# PyNET Library — Codex Instructions

## Required startup context

Before analysing, answering, editing, or running anything in this repository, read these files in full:

1. `CLAUDE.md` — canonical authority for project workflow, Autodesk/PyNET rules, security, execution, and approval policy.
2. `README.md` — repository purpose, supported Autodesk hosts, Python.NET environment, examples, and API-stub usage.

If they conflict, `CLAUDE.md` takes precedence. Do not create a second source of truth by duplicating their detailed guidance here.

## Project scope

This repository is the PyNET Library: production reference scripts and Python-style Autodesk .NET API stubs for automation in Navisworks, Revit, and AutoCAD/Civil 3D through the PyNET Platform and its embedded Python.NET engine.

## Autodesk work

Follow the Router in `CLAUDE.md` before writing a script. Read the host-specific guide and use the relevant example scripts and API stubs before inferring an Autodesk API call. Identify the active host before execution; Navisworks, Revit, and AutoCAD/Civil 3D have different entry points and transaction requirements.

## Codex role

- Implement user-requested changes, review code, and assist with repository maintenance and focused technical work.
- Reuse validated project patterns rather than inventing parallel workflows.
- Keep internal repository AI configuration and persistent documentation in English; reply to users in their language.
