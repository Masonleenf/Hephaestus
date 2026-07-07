---
description: Use the Agentlas browser hardpoint for browser-required work.
argument-hint: <url-or-query>
---
Update fallback: if auto-update fails, run `hephaestus update` once. The current command still works without updating.

# Hephaestus Browser

Raw arguments: `$ARGUMENTS`

Codex plugins cannot register slash commands, so this custom prompt is the
explicit entrypoint: `/prompts:hep-browser`.

Use this when the task needs a real browser, page rendering, login-visible state,
click/form behavior, or JS-heavy evidence. Prefer the Agentlas browser hardpoint
first.

```bash
RUNNER=""
for c in "$HOME/.agentlas/runtime/current/bin/hephaestus" ./bin/hephaestus; do
  [ -x "$c" ] && RUNNER="$c" && break
done
[ -n "$RUNNER" ] || { echo "Hephaestus runtime not found. Run the installer first." >&2; exit 1; }
"$RUNNER" hep-browser "$ARGUMENTS"
```

Report whether `browser.agent_cli` mounted, whether setup is needed, and the
receipt id. If setup is needed, show `hep-browser --setup` and
`hep-browser --check`.
