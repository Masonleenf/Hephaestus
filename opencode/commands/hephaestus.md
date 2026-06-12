---
description: Run the Hephaestus meta-agent — create/package Agentlas agents and teams, or open the ontology GUI.
---

# Hephaestus meta-agent

Raw arguments: `$ARGUMENTS`

Use the `hephaestus-network` skill's runner resolution. If the arguments are
`ontology`, run `"$RUNNER" ontology`. Otherwise classify the request as
single-agent-builder, multi-agent-team-builder, or agentlas-packager, execute
the meta-agent procedure on `$ARGUMENTS`, and include `global_commands` for
the created agent or team in the final response.
