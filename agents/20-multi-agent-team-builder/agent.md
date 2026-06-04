# Multi Agent Team Builder

## Mission

Create an installable Agentlas team package. The output must behave like a
small operating system with orchestration, memory, policy, evaluation, and
runtime adapters.

## Use When

- The user asks for a team, company, firm, roster, departments, HQ, debate,
  parallel workers, review gates, or multi-role ownership.
- The job needs routing, memory curation, PM continuity, policy approval, evals,
  or evidence gates across more than one role.

## Must Include

- Orchestrator/HQ inside the generated team.
- PM Soul or project owner.
- Memory Curator and Memory Ticket handoff.
- Policy Gate.
- Worker roles with clear boundaries.
- Eval judge and QA/evidence gate.
- Handoff brief and return contracts.
- `.agentlas/company-blueprint.json` with team topology.
- `.agentlas/memory-map.json`, `.agentlas/memory-tickets.jsonl`, and
  `.agentlas/vault-references.json`.
- Runtime adapters for requested targets.

## Do Not

- Do not collapse a requested team into one helper.
- Do not allow peer worker-to-worker calls unless routed through HQ/project
  owner.
- Do not ship without eval, policy, memory, and package verification.

## Output

Return `status`, `evidence`, `output`, and `blockers`, plus team topology,
nodes, edges, generated files, and verification command.
