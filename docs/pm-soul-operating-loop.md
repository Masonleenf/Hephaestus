# PM Soul Operating Loop

PM Soul is a continuity layer generated inside Agentlas single-agent and
team-builder outputs when project memory is needed. It keeps product intent,
user promise, unresolved questions, sitemap state, and acceptance criteria alive
between sessions.

## Responsibilities

- Preserve the user-facing job the agent team exists to solve.
- Track product decisions and open loops.
- Keep sitemap changes tied to product intent.
- Define acceptance criteria before implementation.
- Flag drift when an agent optimizes for structure but loses the product job.

## Loop

1. Read `.agentlas/project-soul-memory.md` or the generated project memory file.
2. Extract the current product intent and open loops.
3. Ask the sitemap owner to confirm concept coverage.
4. Translate intent into acceptance criteria.
5. After implementation, update the project-soul memory through a Memory Ticket
   or a verified manual edit.

## Output Shape

```text
PM Soul
- intent:
- audience:
- open_loops:
- acceptance_criteria:
- drift_risks:
- memory_events:
```
