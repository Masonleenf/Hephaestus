---
name: agentlas-core-engine-meta-agent
description: "Use when the user asks for /meta-agent, single agent builder, multi-agent team builder, or packaging an existing local/external agent into Agentlas architecture."
---

# Agentlas Core Engine Meta-Agent

## Procedure

1. Classify the request with the public mode classifier.
2. Ask clarify questions when missing details change the package, adapters, or
   public/private boundary.
3. Route to one of the bundled agents:
   - `single-agent-builder`;
   - `multi-agent-team-builder`;
   - `agentlas-packager`.
4. Preserve `AGENTS.md` as the canonical core.
5. Add or repair `.agentlas` contracts, runtime adapters, memory architecture,
   `.agentlas/global-commands.json`, and verification scripts. Include
   auto-activation seed files when local continuity is part of the output.
6. Add the generated command to Claude Code, Codex, Gemini CLI, generic
   AGENTS.md, and terminal adapters. For teams, expose the orchestrator/HQ
   command and route workers through HQ unless direct worker commands were
   requested.
7. Return `status`, `evidence`, `output`, `global_commands`, and `blockers`.
