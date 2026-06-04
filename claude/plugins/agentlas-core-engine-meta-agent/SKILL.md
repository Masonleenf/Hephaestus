---
name: agentlas-core-engine-meta-agent
description: "Use when the user asks for /meta-agent, single agent builder, multi-agent team builder, or packaging an existing local/external agent into Agentlas architecture."
---

# Agentlas Core Engine Meta-Agent

## Procedure

1. Classify the request as single-agent creation, team creation, or packaging.
2. Route to one of the bundled agents:
   - `single-agent-builder`;
   - `multi-agent-team-builder`;
   - `agentlas-packager`.
3. Preserve `AGENTS.md` as the canonical core.
4. Add or repair `.agentlas` contracts, runtime adapters, memory architecture,
   and verification scripts.
5. Return `status`, `evidence`, `output`, and `blockers`.
