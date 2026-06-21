# Hephaestus Network routing

Route everything typed after this command through the Hephaestus Network
local-first router. Follow the `hephaestus-network` skill exactly: resolve the
runner (`~/.agentlas/runtime/current/bin/hephaestus`, then `./bin/hephaestus`,
then the newest Claude/Codex plugin cache copy), run
`"$RUNNER" auth ensure --timeout 180` first so the browser sign-in opens on
first use and existing Agentlas saved sign-ins are reused silently, then run
`"$RUNNER" route "<request>" --runtime cursor` in the terminal, then act on the
JSON decision (route / clarify / pipeline / hub_fallback / propose_new /
refuse). The router only chooses an agent or fetches a BYOM Hub bundle; actual
tool execution follows Cursor's runtime safety and permission model. **If the routed card declares a local `gui_launcher`** (e.g. a GUI agent like Startup Studio), immediately open its web app BEFORE acting on the decision by running, detached and non-blocking, `python3 <selected.source>/<selected.entrypoints.gui_launcher> &` — so the interactive GUI always appears on any machine with python3. Report the
routing `receipt_id`.
