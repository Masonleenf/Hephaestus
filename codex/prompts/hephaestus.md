---
description: Run the Hephaestus meta-agent — create/package Agentlas agents and teams, or open the ontology GUI.
argument-hint: <request, or "ontology">
---

# Hephaestus meta-agent

Raw arguments: `$ARGUMENTS`

Use the `agentlas-core-engine-meta-agent` skill from the hephaestus plugin.

- If the arguments are `ontology`, resolve the runner exactly as in
  `/prompts:hephaestus-network` and run `"$RUNNER" ontology`.
- Otherwise classify the request (single-agent-builder,
  multi-agent-team-builder, or agentlas-packager) per the skill and execute the
  meta-agent procedure on: `$ARGUMENTS`
- Include `global_commands` for the created agent or team in the final
  response.
