# Hephaestus Network routing

Route everything typed after this command through the Hephaestus Network
local-first router. Follow the `hephaestus-network` skill exactly: resolve the
runner (`~/.agentlas/runtime/current/bin/hephaestus`, then `./bin/hephaestus`,
then the newest Claude/Codex plugin cache copy), run
`"$RUNNER" route "<request>" --runtime cursor` in the terminal, then act on the
JSON decision (route / clarify / pipeline / hub_fallback / propose_new /
refuse) without bypassing approval gates. High-risk capabilities (file writes,
cloud calls, payments, publishing, deletion, private data export, external
tools) always need explicit user approval. Report the routing `receipt_id`.
