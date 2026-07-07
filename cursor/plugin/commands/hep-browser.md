Update fallback: if auto-update fails, run `hephaestus update` once. The current command still works without updating.

# Hephaestus Browser

Use this for browser-required work: rendered pages, JS-heavy sites, click/form
flows, or login-visible evidence. Prefer the Agentlas browser hardpoint first.

Resolve the runner (`~/.agentlas/runtime/current/bin/hephaestus`, then
`./bin/hephaestus`) and run:

`"$RUNNER" hep-browser "<url-or-query>"`

Report whether `browser.agent_cli` mounted, whether setup is needed, and the
receipt id. If setup is needed, show `hep-browser --setup` and
`hep-browser --check`.
