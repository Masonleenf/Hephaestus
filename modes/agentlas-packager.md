# Agentlas Packager

## Purpose

Convert or repair existing agents and teams into Agentlas architecture. Inputs
may come from local prompts, Claude folders, Codex skills, Gemini skills,
Cursor rules, another public repo, a ZIP, or an ad hoc Markdown structure.

## Required Structure

- `AGENTS.md` as canonical core.
- Runtime adapters only as thin mappings.
- `.agentlas/agent-card.json`.
- `.agentlas/company-blueprint.json`.
- `.agentlas/mode-map.json`.
- `.agentlas/memory-map.json`.
- `.agentlas/memory-tickets.jsonl`.
- `.agentlas/vault-references.json`.
- `manifest.json`.
- `scripts/verify-package.sh`.
- `scripts/public_safety_check.sh` for public release.

## Packaging Decisions

1. Decide whether the source is a single-agent package or team package.
2. Preserve useful source behavior.
3. Add missing Agentlas contracts.
4. Remove private or unsafe material before public release.
5. Add Codex plugin, Claude adapter, Gemini adapter, and terminal install
   surfaces when requested.

## Do Not

- Do not claim runtime parity when an adapter only maps the canonical core.
- Do not copy local-only research notes into public output.
- Do not store secret values or raw logs.
