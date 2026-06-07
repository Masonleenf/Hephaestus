---
name: team-builder-packaging
description: "Use when generating a multi-role team package with orchestrator, PM Soul, Memory Curator, policy, eval, QA, handoffs, and runtime adapters."
---

# Team Builder Packaging

Create a full Agentlas team operating system with HQ, PM Soul, Memory Curator,
Policy Gate, workers, eval judge, QA/evidence gate, memory tickets, runtime
adapters, and verification. Expose one orchestrator/HQ global command in
`.agentlas/global-commands.json`; do not expose worker commands unless
requested. Return `global_commands`.
