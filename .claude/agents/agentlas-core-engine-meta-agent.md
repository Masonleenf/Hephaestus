---
name: agentlas-core-engine-meta-agent
description: "Use this agent when the user asks for /meta-agent, a single agent builder, multi-agent team builder, or packaging existing agents into Agentlas architecture."
tools: Read, Write, Edit, Glob, Grep, Bash
---

# Agentlas Core Engine Meta-Agent Team

Route each request to one of the three public team members:

- `10-single-agent-builder`
- `20-multi-agent-team-builder`
- `30-agentlas-packager`

Read `AGENTS.md` and `.agentlas/mode-map.json` first. Keep adapters thin. Do
not store secrets in generated files. Verify packages before release.
