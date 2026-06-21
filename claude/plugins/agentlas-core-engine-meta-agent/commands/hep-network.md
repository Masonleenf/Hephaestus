---
description: Borrow public Agentlas Hub agents through Hephaestus Network.
argument-hint: '<request>'
allowed-tools: Bash, Read, Glob, Grep
---

# /hep-network

Route a natural-language request through the Hephaestus Network local-first
router. Also triggered by `@Hephaestus <request>` in chat.

Raw arguments: `$ARGUMENTS`

## Route

1. Find the first executable Hephaestus runner:

```bash
RUNNER=""
CODEX_HOME_DIR="${CODEX_HOME:-$HOME/.codex}"
for candidate in \
  "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/bin/hephaestus}" \
  "${CODEX_PLUGIN_ROOT:+$CODEX_PLUGIN_ROOT/bin/hephaestus}" \
  "${PLUGIN_ROOT:+$PLUGIN_ROOT/bin/hephaestus}" \
  "$HOME/.agentlas/runtime/current/bin/hephaestus" \
  "./bin/hephaestus" \
  "./claude/plugins/agentlas-core-engine-meta-agent/bin/hephaestus"
do
  if [ -n "$candidate" ] && [ -x "$candidate" ]; then RUNNER="$candidate"; break; fi
done
if [ -z "$RUNNER" ]; then
  for cache in "$HOME/.claude/plugins/cache/agentlas-core-engine/hephaestus" \
               "${CODEX_HOME:-$HOME/.codex}/plugins/cache/agentlas-core-engine/hephaestus"; do
    newest="$(ls -d "$cache"/*/bin/hephaestus 2>/dev/null | sort -V | tail -1)"
    if [ -n "$newest" ] && [ -x "$newest" ]; then RUNNER="$newest"; break; fi
  done
fi
[ -n "$RUNNER" ] || { echo "Hephaestus runtime not found. Run the installer first." >&2; exit 1; }
if [ "${HEPHAESTUS_AUTH_AUTOPOPUP:-1}" != "0" ]; then
  "$RUNNER" auth ensure --timeout 180 >/dev/null 2>&1 || true
fi
DECISION="$("$RUNNER" route "$ARGUMENTS" --runtime claude-code)"
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
   - `action: "route"` — the block above ALREADY auto-launched the GUI if the
     selected card is a local GUI agent (look for `{"gui_autolaunch": "opened"}`
     in the output). Report the selected card (`selected.id`,
     `entrypoints.canonical_command`), tell the user the GUI is opening in the
     browser, then act on the canonical command with the original request. If the
     GUI is the whole interaction (no concrete task given), just confirm it opened.
   - `action: "clarify"` — ask `clarify_question` with the candidate list and re-route with the answer.
   - `action: "pipeline"` — a multi-team plan (e.g. PRD → build → QA). Execute
     `stages` in order: run that stage card's canonical command, save its artifacts under
     `handoff_dir/<order>-<kind>/`, and pass those paths to the next stage.
     On a stage failure: stop and report progress plus the remaining plan —
     never retry silently.
   - `action: "hub_fallback"` or `"hub_candidates"` — Hub lookup used redacted
     keywords only; the raw prompt and local memory were not sent.
   - `action: "propose_new"` — offer to build a new agent/team via `/hep-build`.
   - `action: "refuse"` — explain `reasons` (for example, loop guard). Do not retry around it.

3. Hard rules: the router only chooses an agent or fetches a BYOM Hub bundle.
   Actual tool execution follows the current host runtime's safety and
   permission model. Report the routing `receipt_id` in your final message.

## Examples

```text
/hep-network turn these meeting notes into a weekly report
/hep-network 이 작업에 맞는 에이전트 찾아줘
@Hephaestus draft a launch plan for my product
```
