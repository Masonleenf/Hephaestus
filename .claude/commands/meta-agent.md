# /meta-agent

Invoke the Agentlas Core Engine Meta-Agent Team.

## Route

1. Read project `AGENTS.md`.
2. Read `.agentlas/mode-map.json`.
3. Pick one:
   - `agents/10-single-agent-builder/agent.md` for one worker package.
   - `agents/20-multi-agent-team-builder/agent.md` for a team package.
   - `agents/30-agentlas-packager/agent.md` for existing agent/team packaging.
4. Load matching skills only.
5. Return `status`, `evidence`, `output`, and `blockers`.

## Examples

```text
/meta-agent create a self-evolving research agent
/meta-agent create an investment analyst team
/meta-agent package this existing Claude agent into Agentlas architecture
```
