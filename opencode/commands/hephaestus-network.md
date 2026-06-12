---
description: Route a request through the Hephaestus Network local-first router (cards, Hub fallback, approval gates).
---

# Hephaestus Network routing

Raw arguments: `$ARGUMENTS`

1. Resolve the runner — first executable wins:

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
[ -n "$RUNNER" ] || { echo "Hephaestus runtime not found. Run the installer first." >&2; exit 1; }
"$RUNNER" route "$ARGUMENTS" --runtime opencode
```

2. Act on the returned JSON decision — never bypass it:
   - `route` — report the selected card; if `approval_request` is present, get
     explicit user approval for the listed capabilities first, then invoke the
     selected agent's canonical command with the original request.
   - `clarify` — ask `clarify_question` with the candidates and re-route.
   - `pipeline` — execute `stages` in order behind per-stage approvals, save
     artifacts under `handoff_dir/<order>-<kind>/`, pass paths forward; on a
     stage failure stop and report — never retry silently.
   - `hub_fallback` / `hub_candidates` — show
     `approval_request.payload_preview` (redacted keywords only); after
     explicit approval re-run with `--approve-hub`.
   - `propose_new` — offer to build a new agent/team via the Hephaestus
     meta-agent.
   - `refuse` — explain `reasons`; do not retry around the guard.

3. Hard rules: local memory stays local without explicit export approval;
   never auto-run `file_write`, `cloud_call`, `payment`, `publish`, `delete`,
   `private_data_export`, or `external_tool`; report the routing `receipt_id`
   in the final message.
