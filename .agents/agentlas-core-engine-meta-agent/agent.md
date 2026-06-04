# Agentlas Core Engine Meta-Agent Team

Use this portable team when the user wants to create, audit, repair, or package
an Agentlas-compatible agent or agent-team repository.

## Route

1. Read root `AGENTS.md`.
2. Read `.agentlas/mode-map.json`.
3. Pick exactly one core team member:
   - `10-single-agent-builder`;
   - `20-multi-agent-team-builder`;
   - `30-agentlas-packager`.
4. Read `.agentlas/memory-map.json`.
5. Select relevant skills from `.agents/skills`.
6. Verify with `scripts/verify-package.sh`.

## Output

Return `status`, `evidence`, `output`, and `blockers`.
