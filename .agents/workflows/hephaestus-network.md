# /hephaestus-network

Route a natural-language request through the Hephaestus Network local-first
router (routing cards → local agents/teams/plugins → Hub fallback with
approval). Also triggered by `@Hephaestus <request>`.

## Engine resolution

Use the first executable found:

1. `./bin/hephaestus` (workspace copy)
2. `~/.claude/plugins/cache/agentlas-core-engine/hephaestus/*/bin/hephaestus`
3. `${CODEX_HOME:-~/.codex}/plugins/cache/agentlas-core-engine/hephaestus/*/bin/hephaestus`
4. `./claude/plugins/agentlas-core-engine-meta-agent/bin/hephaestus`

## Steps

1. Run `"$RUNNER" route "<request>" --runtime antigravity` and parse the JSON.
2. Act on `action`:
   - `route` — report the selected card and canonical command; if
     `approval_request` exists, get explicit user approval before invoking.
   - `clarify` — ask the `clarify_question` with candidates, then re-route.
   - `hub_fallback` / `hub_candidates` — ask the user to approve the Hub
     search/use first (only redacted keywords are sent, never raw prompts);
     re-run with `--approve-hub` after approval.
   - `propose_new` — offer to build a new agent/team via `/hephaestus`.
   - `refuse` — explain `reasons`; do not work around the loop guard or
     privacy block.
3. Hard rules: local memory never leaves the machine without explicit export
   approval; high-risk capabilities always require user approval; include the
   routing `receipt_id` in the final answer.
