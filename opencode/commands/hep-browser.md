---
description: Use the Agentlas browser hardpoint for browser-required work.
---
Update fallback: if auto-update fails, run `hephaestus update` once. The current command still works without updating.

# Hephaestus Browser

Raw arguments: `$ARGUMENTS`

```bash
RUNNER=""
for c in "$HOME/.agentlas/runtime/current/bin/hephaestus" ./bin/hephaestus; do
  [ -x "$c" ] && RUNNER="$c" && break
done
[ -n "$RUNNER" ] || { echo "Hephaestus runtime not found. Run the installer first." >&2; exit 1; }
"$RUNNER" hep-browser "$ARGUMENTS"
```

Use this for rendered/browser-required work and report the `browser.agent_cli`
status plus receipt id. If setup is needed, show `hep-browser --setup` and
`hep-browser --check`.
