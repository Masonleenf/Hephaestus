# Mode Classifier

The mode classifier chooses which Agentlas meta-agent mode should handle a user
request before any package is generated.

Every runtime should use the same public classification order even if it
implements the classifier in code, prompts, buttons, or a local command.

## Output

Return exactly one mode:

- `single-agent-creator`
- `team-builder`
- `agentlas-packager`

If the request is too ambiguous to classify, run the clarify question loop
instead of guessing.

## Classification Order

### 0. Agentlas Packager

Choose `agentlas-packager` when the user already has something and wants it
converted, repaired, cleaned, imported, or released.

Strong signals:

- existing agent, prompt, team, repo, folder, ZIP, plugin, or adapter;
- "package this", "convert this", "repair this", "make it Agentlas-ready";
- "Claude agent", "Codex agent", "Gemini agent", "Cursor agent",
  `AGENTS.md`, `CLAUDE.md`, or `GEMINI.md`;
- public release, open-source cleanup, adapter creation, or compatibility pass;
- Korean equivalents such as `기존`, `이미 만든`, `패키징`, `Agentlas 구조로`,
  `레포`, `저장소`, `폴더`, `ZIP`.

Packaging wins over team-building. If the user says "this existing team", it is
still packager first because the first job is inspection and repair.

### 1. Independent Ownership Boundary Count

Do not classify by the keyword "team" alone. Count roles that must
independently own all three:

- their own memory/context;
- their own tools/permissions;
- their own success criteria.

One independent ownership boundary means `single-agent-creator`.
Two or more boundaries means a `team-builder` candidate.
If the count is unclear, run the clarify question loop before generation.
The user-facing question must be plain language, for example: "이 일을 한 명의
전문가가 처음부터 끝까지 맡으면 되나요, 아니면 조사/분석/검토처럼 여러
전문가가 나눠 맡고 마지막에 합쳐야 하나요?"

### 2. Synthesis Need

For a multi-boundary candidate, choose `team-builder` only when the role outputs
must be routed, reviewed, synthesized, or chained through produces/consumes
dependencies. If the roles are unrelated, build separate single-agent packages
instead of one team.

Strong signals:

- separate memory partitions (strongest signal);
- tools or permissions that must not be merged into one worker;
- review/policy separation between roles;
- produces/consumes handoff or pipeline dependencies;
- roster, desk, HQ, departments, review gates, QA, eval, PM, or Memory Curator.

### 3. Single Agent Creator

Choose `single-agent-creator` when the request is for one installable worker.

Strong signals:

- one assistant, one specialist, one worker, one skill package;
- no requested roster or multi-role topology;
- a single goal that can be handled by one agent with multiple skills;
- several tools or skills, but one worker owns the memory/context and success
  criteria;
- no routing, review handoff, or final synthesis requirement.

## Shape Guard

Generated packages must be exactly one of two shapes:

- SINGLE: one worker `agent.md`, no orchestrator/HQ, and
  `.agentlas/company-blueprint.json` topology `single-agent`.
- TEAM: two or more worker roles plus orchestrator/HQ, blueprint topology with
  nodes/edges, PM Soul, Memory Curator, Policy Gate, eval judge, QA/evidence
  gate, Memory Tickets, and one HQ public command.

Multiple loose worker `agent.md` files without orchestrator/HQ and blueprint
topology are a degenerate team and must fail verification.

## Ambiguity Rule

Ask clarification when:

- the user asks for an "agent team" but names only one job;
- the user asks for an "agent" but also lists several independent departments;
- the user gives a domain label plus "team" but does not define memory/context
  ownership, role count, tool/permission separation, synthesis need, or
  execution order;
- the user says "package" without providing or pointing to existing material;
- the target runtime or public/private boundary changes the output.

Use `docs/clarify-question-loop.md` for the question format.

## Examples

| Request | Mode | Why |
|---|---|---|
| "Make me a research agent" | `single-agent-creator` | one ownership boundary |
| "Build a marketing agency with strategist, copywriter, designer, QA" | `team-builder` | multi-role roster |
| "Convert this Claude agent repo into Agentlas architecture" | `agentlas-packager` | existing repo |
| "Package my local team for Codex and Claude" | `agentlas-packager` | existing team plus adapters |
| "Create an AI company that writes reports" | `team-builder` | company-style topology |
| "Build a stock research team" | `needs_clarification` | domain label plus "team" does not prove ownership boundaries |

## Portable Pseudocode

```text
if prompt references existing agent/team/repo/folder/zip or asks to package/convert/repair:
  return agentlas-packager

boundaries = count_roles_that_need_independent_memory_tools_and_success_criteria(prompt)
if boundaries is unclear:
  return needs_clarification

if boundaries >= 2:
  if outputs_need_routing_synthesis_or_produces_consumes_handoff(prompt):
    return team-builder
  return separate_single_agent_packages

if boundaries == 1:
  return single-agent-creator

return needs_clarification
```
