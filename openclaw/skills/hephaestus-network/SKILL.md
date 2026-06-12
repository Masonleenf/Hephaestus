---
name: hephaestus-network
description: "Use when the user types /hephaestus-network, mentions @Hephaestus, or asks to find/route to the right local agent, team, or plugin for a task. Routes natural-language requests through the Hephaestus Network local-first router with Hub fallback behind user approval."
metadata: {"openclaw": {"emoji": "🔨", "requires": {"bins": ["python3"]}, "homepage": "https://github.com/agentlas-ai/Hephaestus"}}
---

# Hephaestus Network Routing

Route the request through the deterministic local-first router via the `exec`
tool. Never guess an agent yourself when this skill is active — the router
decides.

## 1. Resolve the runner

Run this resolution with `exec` and use the first hit:

```bash
RUNNER=""
for c in \
  "$HOME/.agentlas/runtime/current/bin/hephaestus" \
  ./bin/hephaestus
do [ -x "$c" ] && RUNNER="$c" && break; done
if [ -z "$RUNNER" ]; then
  for cache in \
    "$HOME/.claude/plugins/cache/agentlas-core-engine/hephaestus" \
    "$HOME/.codex/plugins/cache/agentlas-core-engine/hephaestus"; do
    newest="$(ls -d "$cache"/*/bin/hephaestus 2>/dev/null | sort -V | tail -1)"
    [ -n "$newest" ] && [ -x "$newest" ] && RUNNER="$newest" && break
  done
fi
```

If no runner exists, tell the user to run the one-touch installer:
`curl -fsSL https://raw.githubusercontent.com/agentlas-ai/Hephaestus/main/scripts/install-all-runtimes.sh | bash`

## 2. Route

```bash
"$RUNNER" route "<the user's request>" --runtime openclaw
```

## 3. Act on the JSON decision — never bypass it

- `route` — report the selected card (`selected.id`,
  `entrypoints.canonical_command`). If `approval_request` is present, get the
  user's explicit approval for the listed capabilities FIRST, then invoke the
  selected agent's canonical command with the original request.
- `clarify` — ask `clarify_question` with the candidate list and re-route with
  the answer.
- `pipeline` — execute `stages` in order: per-stage approval first, run the
  stage card's canonical command, save artifacts under
  `handoff_dir/<order>-<kind>/`, pass those paths to the next stage. On a stage
  failure: stop and report progress plus the remaining plan — never retry
  silently.
- `hub_fallback` / `hub_candidates` — show
  `approval_request.payload_preview` (redacted keywords only — the raw prompt
  is never sent). Only after explicit approval re-run with `--approve-hub`.
- `propose_new` — offer to build a new agent/team via the Hephaestus
  meta-agent.
- `refuse` — explain `reasons` (loop guard or privacy block). Do not retry
  around it.

## 4. Hard rules

- Local memory stays local unless the user explicitly approves an export.
- Never auto-run `file_write`, `cloud_call`, `payment`, `publish`, `delete`,
  `private_data_export`, or `external_tool` capabilities without user approval.
- Report the routing `receipt_id` in your final message.
