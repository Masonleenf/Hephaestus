---
name: multi-agent-team-builder
description: "Create a multi-role Agentlas team package with orchestrator, PM Soul, Memory Curator, Policy Gate, eval, QA, handoffs, and runtime adapters."
tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
---

# Multi Agent Team Builder

Create an installable team package. Include orchestrator/HQ, PM Soul, Memory
Curator, Memory Tickets, Policy Gate, workers, eval judge, QA/evidence gate,
handoff rules, runtime adapters, and verification.

Add `.agentlas/global-commands.json` with one orchestrator/HQ global command
across Claude Code, Codex, Gemini CLI, generic AGENTS.md, and terminal adapters.
Route workers through HQ unless direct worker commands were explicitly
requested. Build separate roles only for independent ownership boundaries:
memory/context, tools/permissions, and success criteria. If the user only gives
a domain label plus "team", ask the ownership-boundary question before
generation. Run `scripts/verify-team-package.sh <package-root>` before
reporting `completed`; if it fails, add orchestrator/HQ plus blueprint topology
or collapse to a valid single-agent package. Return `global_commands` in the
final handoff.
