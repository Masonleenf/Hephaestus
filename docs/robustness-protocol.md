# Hephaestus Stormbreaker Robustness Protocol

Hephaestus Stormbreaker is the public name for the Hephaestus Robustness
Protocol. It is a global operating protocol for coding agents. It is not a
model, standalone agent, skill, leaked prompt, or Hephaestus Network routing
card.

The protocol sits above local agents, Hub bundles, skills, and tools. Its job
is to make long-running work harder to abandon, harder to falsely declare done,
and easier to recover after context loss or a failed verification pass.

The strongest current claim is operational robustness, not raw benchmark
correctness. Local scorecards show Stormbreaker leading native Codex and a
baseline Hephaestus Network arm on process-aware robustness metrics, while the
strict 30-task SWE-bench Lite pilot does not show public benchmark superiority.

## Research Sources

The protocol distills recurring patterns from public agent harnesses and local
research notes:

- Superpowers: approval before implementation, TDD, subagent execution, review,
  and verification-before-completion.
- GSD Core: discuss, plan, execute, verify, ship phase loops with fresh-context
  executors and durable state files.
- LazyCodex / oh-my-claudecode / Gajae-Code: interview, consensus planning,
  goal ledgers, replay artifacts, bounded loops, and completion gates.
- FableCodex / Fable-style operating protocol repos: requirements ledgers,
  evidence checkpoints, final verification gates, and model-aware delegation.
- NightWatch-style recorders: logs are claims; independent replay or artifact
  checks are stronger proof.
- Reflexion (<https://arxiv.org/abs/2303.11366>): failed checks become verbal
  failure memory for later attempts.
- Self-Refine (<https://arxiv.org/abs/2303.17651>): feedback and refinement
  form a bounded test-time improvement loop without model retraining.
- SWE-agent / Agent-Computer Interface
  (<https://arxiv.org/abs/2405.15793>): agent-computer interface design
  matters; agents need stable navigation, edit, diff, and test surfaces.

These are used as engineering precedents, not as private system prompts or
vendor behavior clones.

## Protocol State

Every substantial task should move through these states:

1. `scope_lock`
   - Restate the exact task, owner repo, mutation boundary, and non-goals.
   - Clarify before mutation when a missing answer would change files, costs,
     security posture, or public release state.

2. `issue_contract`
   - Extract behavior that must change, behavior that must not change, files
     likely in scope, public checks, and issue-implied edge classes.
   - Treat this as the bridge between a natural-language request and verifier
     evidence.

3. `failure_memory`
   - Check the task against public-safe failure classes before patching:
     Unicode normalization, length limits, migration/defaulting, retry timing,
     atomic writes, parser edge cases, time/date APIs, package metadata gaps,
     and unsupported README claims.
   - This is not private-oracle leakage; it is a reusable checklist built from
     observed failure modes.

4. `verifier_first_plan`
   - Produce a short staged plan for risky or multi-file work.
   - Define the verification command, expected artifact, and final exit gate
     before implementation begins.

5. `evidence_loop`
   - Execute one bounded change batch at a time.
   - After each failure, record the failing evidence, change one hypothesis, and
     retry within a declared cap.
   - Tests are evidence, not the whole definition of done.

6. `review_gate`
   - Check scope drift, destructive changes, unrelated file edits, secret
     exposure, and unsupported claims.
   - For high-risk work, run a reviewer path or independent verification script.

7. `outcome_ledger`
   - Record final evidence, failed attempts, unresolved risks, and follow-up
     gates in a short durable note or result row.
   - Make continuation after context loss possible.

8. `final_gate`
   - Do not finish unless required checks passed, blockers are empty or clearly
     reported, artifacts exist, and the final answer separates verified facts
     from remaining risk.

## Risk Tiers

| Tier | Examples | Required Gate |
| --- | --- | --- |
| `low` | single doc edits, read-only analysis | scope lock + final gate |
| `medium` | scripts, tests, package docs, local-only automation | plan lock + evidence loop |
| `high` | release, auth, private data, publishing, destructive changes | explicit approval + review gate |

## Bounded Retry

Robustness is not infinite looping. A failed verification may retry only when
there is new evidence and a narrower hypothesis.

Default caps:

- Same verification failure: 2 retries.
- Whole task loop: 3 rounds.
- External-state blockers: stop after evidence shows the same blocker twice.

When a cap is hit, report the blocker and the last evidence instead of
inventing success.

## Completion Contract

A final answer may claim completion only when all are true:

- Task scope is satisfied.
- Required files/artifacts exist.
- Verification commands ran or the reason they could not run is explicit.
- Failed checks are not hidden behind wording like "should work".
- Public or user-facing outputs passed the relevant safety gate.
- Follow-up work is framed as optional improvement, not required completion.

## Relationship To Hephaestus Network

Hephaestus Network chooses agents and Hub bundles. The Robustness Protocol
governs execution after a route is selected, and also governs native Codex runs
when no agent or skill is used.

This makes it suitable for three-way evaluation:

1. native runtime with no added protocol;
2. Hephaestus Network routing and agent calls;
3. Hephaestus Network plus Stormbreaker gates.
