---
name: self-evolving-single-agent
description: "Use when a single installable agent should keep learning, refresh research, track sources, or propose repairs without becoming a multi-agent team."
---

# Self-Evolving Single Agent

Keep the output as one worker, add memory architecture, and make
self-evolution proposal-first with human approval before changing tools,
connectors, secrets, or core instructions. Add `.agentlas/global-commands.json`
and one public global command across Claude Code, Codex, Gemini CLI, generic
AGENTS.md, and terminal adapters. Return `global_commands`.
