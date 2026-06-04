# Chain Map

This is the default execution chain for the three-agent meta-agent team.

## Chain

1. Root `AGENTS.md` receives the user request and classifies the job.
2. It routes to exactly one core team member:
   - `10-single-agent-builder`;
   - `20-multi-agent-team-builder`;
   - `30-agentlas-packager`.
3. The selected agent emits or repairs the Agentlas architecture contracts.
4. Runtime adapters are generated as thin mappings over `AGENTS.md`.
5. Verification checks package shape, JSON validity, skill frontmatter, public
   safety, and plugin readiness when requested.

## Mode-Specific Output

Single-agent output must include:

- one worker contract;
- reusable skills;
- memory architecture;
- optional self-evolution or research-refresh loop;
- runtime adapters.

Team output must include:

- orchestrator/HQ;
- PM Soul or project owner;
- Memory Curator and Memory Tickets;
- Policy Gate;
- worker roles;
- eval judge;
- QA/evidence gate;
- handoff and return contracts;
- runtime adapters.

Packager output must include:

- classification of the existing source;
- repaired Agentlas contracts;
- public/private cleanup;
- manifest and install surface;
- verification results.

## Required Concept Coverage

- Three-agent meta-team: `agents/`
- Mode map: `.agentlas/mode-map.json`
- Memory architecture: `.agentlas/memory-map.json`
- Sitemap/task bias: `.agentlas/sitemap.json`
- LLM runtime architecture: `docs/llm-runtime-architecture.md`
- Package verification: `scripts/verify-package.sh`

If any concept is intentionally skipped, record the reason in
`.agentlas/validation-ledger.jsonl`.
