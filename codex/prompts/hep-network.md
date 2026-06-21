---
description: Route a request through the Hephaestus Network local-first router (cards, Hub fallback).
argument-hint: <natural-language request>
---

# Hephaestus Network routing

Raw arguments: `$ARGUMENTS`

Codex plugins cannot register slash commands, so this custom prompt is the
explicit entrypoint (`/prompts:hep-network`). The same contract is also
available implicitly via the `hephaestus-network` skill.

1. Resolve the runner — first executable wins:

```bash
RUNNER=""
for c in \
  "$HOME/.agentlas/runtime/current/bin/hephaestus" \
  ./bin/hephaestus
do [ -x "$c" ] && RUNNER="$c" && break; done
if [ -z "$RUNNER" ]; then
  for cache in \
    "${CODEX_HOME:-$HOME/.codex}/plugins/cache/agentlas-core-engine/hephaestus" \
    "$HOME/.claude/plugins/cache/agentlas-core-engine/hephaestus"; do
    newest="$(ls -d "$cache"/*/bin/hephaestus 2>/dev/null | sort -V | tail -1)"
    [ -n "$newest" ] && [ -x "$newest" ] && RUNNER="$newest" && break
  done
fi
[ -n "$RUNNER" ] || { echo "Hephaestus runtime not found. Run the installer first." >&2; exit 1; }
if [ "${HEPHAESTUS_AUTH_AUTOPOPUP:-1}" != "0" ]; then
  "$RUNNER" auth ensure --timeout 180 >/dev/null 2>&1 || true
fi
DECISION="$("$RUNNER" route "$ARGUMENTS" --runtime codex)"
printf '%s\n' "$DECISION"

# Deterministic local GUI auto-launch (Network surface). If the router selected a
# LOCAL card that declares a gui_launcher, open its GUI right now — DETACHED and
# non-blocking — so `/hep-network <gui agent>` ALWAYS shows the GUI on any machine,
# regardless of how the agent later acts on the routing decision. Hub/remote cards
# (no local source dir) and cards without a gui_launcher are never launched.
# Disable with HEPHAESTUS_GUI_AUTOLAUNCH=0.
if [ "${HEPHAESTUS_GUI_AUTOLAUNCH:-1}" != "0" ]; then
  printf '%s' "$DECISION" | python3 -c '
import sys, json, os, subprocess
try:
    d = json.load(sys.stdin)
except Exception:
    raise SystemExit(0)
if d.get("action") != "route":
    raise SystemExit(0)
sel = d.get("selected") or {}
ep = sel.get("entrypoints") or {}
launcher = ep.get("gui_launcher") or ""
source = sel.get("source") or ""
if not (launcher and isinstance(source, str) and os.path.isdir(source)):
    raise SystemExit(0)
path = os.path.join(source, launcher)
if not os.path.isfile(path):
    print(json.dumps({"gui_autolaunch": "skipped", "reason": "launcher_missing", "path": path}))
    raise SystemExit(0)
try:
    subprocess.Popen(
        [sys.executable, path],
        cwd=source,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    print(json.dumps({"gui_autolaunch": "opened", "launcher": path}))
except Exception as e:
    print(json.dumps({"gui_autolaunch": "error", "error": str(e)}))
'
fi
```

2. Act on the returned JSON decision:
   - `route` — report the selected card, then invoke the selected agent's
     canonical command with the original request.
   - `clarify` — ask `clarify_question` with the candidates and re-route.
   - `pipeline` — execute `stages` in order, save artifacts under
     `handoff_dir/<order>-<kind>/`, pass paths forward; on a stage failure stop
     and report — never retry silently.
   - `hub_fallback` / `hub_candidates` — Hub lookup used redacted keywords only;
     the raw prompt and local memory were not sent.
   - `propose_new` — offer to build a new agent/team via `/hep-build`.
   - `refuse` — explain `reasons`; do not retry around the guard.

3. Hard rules: the router only chooses an agent or fetches a BYOM Hub bundle.
   Actual tool execution follows the current host runtime's safety and
   permission model. Report the routing `receipt_id` in the final message.
