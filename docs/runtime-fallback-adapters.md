# Runtime registration and fallback adapters

How `/hephaestus` and `/hephaestus-network` get registered per runtime, and
what to do where automatic command registration is not possible.

| Runtime | Registration | Mechanism |
|---------|--------------|-----------|
| Claude Code | automatic | plugin install + `~/.claude/commands/*.md` (one-touch installer) |
| Codex | automatic | `codex plugin add hephaestus@agentlas-core-engine` |
| Gemini CLI | automatic (partial) | `gemini extensions install …` + fallback TOML copied to `~/.gemini/commands/` |
| Antigravity | automatic | global workflow copied to `~/.gemini/antigravity*/global_workflows/` |
| Cursor | manual fallback | copy `cursor/rules/hephaestus.mdc` into `<project>/.cursor/rules/`; the rule reacts to `/hephaestus`, `/hephaestus-network`, and `@Hephaestus` mentions (Cursor has no custom slash commands) |
| Terminal | automatic | `bin/hephaestus` — `hephaestus "<request>"` routes directly |
| Generic AGENTS.md runtimes | manual fallback | the AGENTS.md command alias section; the runtime reads AGENTS.md and treats `/hephaestus*` or `@Hephaestus` as the routing contract |
| Gemma / local model runtimes | manual fallback | same as generic AGENTS.md: include this repo's `AGENTS.md` in the model context, and run `bin/hephaestus route "<request>"` via the runtime's shell tool when available |
| Opened Hermes / Hermes-like local runtimes | manual fallback | if the runtime supports tool/shell calls, wire `bin/hephaestus route`; otherwise paste the decision JSON workflow from `.claude/commands/hephaestus-network.md` |

Realistic limits, stated plainly:

- Cursor and AGENTS.md-only runtimes cannot register slash commands — the
  fallback is a rules/instructions file, which the installer cannot place into
  arbitrary projects. Copy it per project.
- Local model runtimes vary; the only universal contract is: (1) read
  AGENTS.md, (2) call `bin/hephaestus route`, (3) honor the decision JSON and
  its approval gates.
- If command registration fails anywhere, the terminal form always works:
  `hephaestus "<request>"`.

First-use memory behavior: whichever runtime calls the router first triggers
`network init` (also run by the installer). All later calls from any runtime
reuse the same `~/.agentlas/networking/` — one local memory map, no per-runtime
copies.
