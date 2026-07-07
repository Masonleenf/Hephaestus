---
description: Use the Agentlas browser hardpoint for browser-required work.
argument-hint: '<url-or-query>'
allowed-tools: Bash, Read, Glob, Grep
---
Update fallback: if auto-update fails, run `hephaestus update` once. The current command still works without updating.

# /hep-browser

Use this when the task needs a real browser, page rendering, login-visible state,
click/form behavior, or JS-heavy evidence. Prefer the Agentlas browser hardpoint
first; do not route browser work through generic research commands unless this
command reports that the hardpoint is unavailable.

Raw arguments: `$ARGUMENTS`

## Run

```bash
RUNNER=""
for candidate in \
  "$HOME/.agentlas/runtime/current/bin/hephaestus" \
  "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/bin/hephaestus}" \
  "${PLUGIN_ROOT:+$PLUGIN_ROOT/bin/hephaestus}" \
  "./bin/hephaestus"
do
  if [ -n "$candidate" ] && [ -x "$candidate" ]; then RUNNER="$candidate"; break; fi
done
[ -n "$RUNNER" ] || { echo "Hephaestus runtime not found. Run the installer first." >&2; exit 1; }
"$RUNNER" hep-browser "$ARGUMENTS"
```

## Answer Shape

1. Report whether `browser.agent_cli` was mounted or needs setup.
2. If setup is needed, show `hep-browser --setup` and `hep-browser --check`.
3. Include the receipt id and the browser module chain.

## Examples

```text
/hep-browser https://example.com
/hep-browser login page render check
/hep-browser --setup
/hep-browser --check
```
