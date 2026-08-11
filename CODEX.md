<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2024-2026 RAEN Digital Tools SL - PyNET Platform -->

# Codex Notes

This agent acts as a complement to Claude in this repository.

## Precedence

- `CLAUDE.md` is the canonical authority for project-specific AI guidance.
- If there is any conflict between this file and `CLAUDE.md`, `CLAUDE.md` takes precedence.
- Do not create a second source of truth for PyNET, Navisworks, or project workflow rules that already exist in `CLAUDE.md`.

## Codex Role

- Implement changes requested by the user.
- Review code and identify risks or regressions.
- Help with repository maintenance, automation, and focused technical tasks.
- Reuse the project context and workflow already defined for Claude instead of redefining it.

## Boundaries

- Keep project rules, domain workflow, execution constraints, and approval policy in `CLAUDE.md`.
- Use this file only for Codex-specific working notes or lightweight behavioral guidance.
- Prefer referencing existing guidance over duplicating it.

## Language Policy

- All internal agent configuration, skills, command files, and persistent AI documentation must be written in English.
- User-facing conversation should match the user's language.
- If the user writes in Spanish, reply in Spanish.
- If the user writes in English, reply in English.
- In case of doubt, keep persistent repository AI artifacts in English.
