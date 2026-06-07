---
name: agentlas-packaging
description: "Use when converting, repairing, or packaging an existing local or external agent/team into Agentlas architecture for local install, Agentlas import, Codex plugin use, Claude adapter use, or open-source release."
---

# Agentlas Packaging

## Procedure

1. Inspect the existing source: prompt, repo, ZIP, runtime folder, skill, command,
   or generated agent package.
2. Classify it as single-agent, team-builder, or mixed/unclear.
3. Preserve useful behavior while adding Agentlas contracts:
   - `AGENTS.md`;
   - `.agentlas/agent-card.json`;
   - `.agentlas/company-blueprint.json`;
   - `.agentlas/mode-map.json`;
   - `.agentlas/memory-map.json`;
   - `.agentlas/memory-tickets.jsonl`;
   - `.agentlas/vault-references.json`;
   - `.agentlas/global-commands.json`;
   - runtime adapters;
   - verification scripts.
4. Add or repair the global command across Claude Code, Codex, Gemini CLI,
   generic AGENTS.md tools, and terminal adapters.
5. Remove secrets, raw logs, private local notes, and unsafe public paths.
6. Run package verification and public-safety checks before release.

## Output

Return `classification`, `repaired_files`, `agentlas_contracts_added`,
`runtime_adapters`, `global_commands`, `verification`, and `blockers`.
