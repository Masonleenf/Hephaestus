---
name: team-builder-packaging
description: "Use when generating or auditing a multi-role agent team package with orchestrator, PM Soul, Memory Curator, Policy Gate, workers, eval, QA, handoffs, and runtime adapters."
---

# Team Builder Packaging

## Procedure

1. Start with the orchestrator/HQ.
2. Add PM Soul or project owner.
3. Add Memory Curator and Memory Ticket handoff.
4. Add Policy Gate, eval judge, and QA/evidence gate.
5. Add workers only for real domain ownership.
6. Encode handoff and return contracts.
7. Emit one orchestrator/HQ global command in `.agentlas/global-commands.json`
   and runtime command files. Do not expose worker commands unless requested.
8. Emit runtime adapters and package verification.

## Output

Return `team_topology`, `nodes`, `edges`, `memory_architecture`, `gates`,
`runtime_adapters`, `global_commands`, and `verification`.
