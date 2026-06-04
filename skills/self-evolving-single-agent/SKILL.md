---
name: self-evolving-single-agent
description: "Use when generating a single installable agent that should keep learning, track sources, refresh research, propose repairs, or improve itself over time without becoming a multi-agent team."
---

# Self-Evolving Single Agent

## Procedure

1. Keep the package as one worker unless the user asks for a team.
2. Add memory architecture even for the single worker:
   - `.agentlas/memory-map.json`;
   - `.agentlas/vault-references.json`;
   - project memory owned by PM Soul/project owner;
   - Memory Events and Memory Tickets for durable updates.
3. If the task depends on current sources, add a research-refresh command,
   watchlist memory section, references, and optional scheduled workflow.
4. Make self-evolution proposal-first: draft patches or repair kits, then wait
   for human approval before changing tools, connectors, secrets, or core
   instructions.

## Output

Return `agent_package`, `skills`, `memory_contract`, `refresh_loop`,
`approval_gate`, and `verification`.
