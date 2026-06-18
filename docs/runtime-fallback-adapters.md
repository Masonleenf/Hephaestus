# Runtime registration and fallback adapters

How `/hephaestus-build`, `/hephaestus-network`, `/hephaestus-cloud`,
`/hephaestus-search`, and `/hephaestus-call` get registered per runtime, and
what to do where automatic command registration is not possible.

Two universal surfaces underpin everything (installed by the one-touch
installer):

- **Runtime home** — `~/.agentlas/runtime/current/bin/hephaestus` is the
  runtime-neutral runner every adapter resolves first.
- **Universal skill** — `~/.agents/skills/hephaestus-network/SKILL.md`
  (AgentSkills spec) is read natively by Codex, OpenCode, OpenClaw, Cursor,
  and Crush.

| Runtime | Registration | Mechanism |
|---------|--------------|-----------|
| Claude Code | automatic | plugin install (commands + `hephaestus-network` skill) + `~/.claude/commands/*.md` |
| Codex | automatic | `codex plugin add hephaestus@agentlas-core-engine` (skills — plugins cannot register slash commands) + custom prompts `~/.codex/prompts/` → `/prompts:hephaestus-network` + local MCP in `~/.codex/config.toml` |
| Gemini CLI | automatic (partial) | `gemini extensions install …` (commands TOML + skill) + fallback TOML copied to `~/.gemini/commands/` |
| Antigravity | automatic | global workflow copied to `~/.gemini/antigravity*/global_workflows/` |
| Cursor | automatic | commands → `~/.cursor/commands/` (IDE + `agent` CLI), skill → `~/.cursor/skills/` and `~/.agents/skills/`; `cursor/plugin/` is the marketplace-ready plugin bundle; `cursor/rules/hephaestus.mdc` remains the per-project rule fallback |
| OpenCode | automatic | commands → `~/.config/opencode/commands/` → `/hephaestus-network`; skill via `~/.agents/skills`; MCP via `opencode.json` (see `opencode/README.md`) |
| OpenClaw | automatic | AgentSkills skill → `~/.openclaw/skills` (or `openclaw skills install --global`); invoke `/skill hephaestus-network <request>`; exec-tool gated on `python3` |
| Hermes Agent | automatic | AgentSkills skill → `~/.hermes/skills/`; MCP server in `~/.hermes/config.yaml` (see `hermes/README.md`) |
| Terminal | automatic | `bin/hephaestus-build`, `bin/hephaests-network`, `bin/hephaestus-search`, `bin/hephaestus-call`, and `bin/hephaestus` — `Hephaestus-build "<request>"` builds, `hephaests-network "<request>"` borrows Hub agents, `hephaestus cloud "<request>"` uses the signed-in user's cloud packages, `Hephaestus-search "<request>"` compares Cloud/Hub candidates, and `Hephaestus-call "agent-a,agent-b" "<context>"` prepares exact agents |
| Ollama / Gemma / DeepSeek local models | via harness or MCP | `ollama launch <harness>` then use that harness's surface above; or register `hephaestus mcp serve` (stdio MCP, tools `hephaestus_route` / `hephaestus_network_status`); raw API loops use an OpenAI-`tools` function — see `docs/local-models.md` |
| Generic AGENTS.md runtimes | manual fallback | the AGENTS.md command alias section; the runtime reads AGENTS.md and treats `/hephaestus*` or `@Hephaestus` as the routing contract |

Realistic limits, stated plainly:

- Codex plugins cannot contribute slash commands (loader reads `skills/`,
  `hooks/`, `.mcp.json`, `.app.json` only) — the explicit slash surface is the
  deprecated-but-functional custom prompts dir, namespaced as
  `/prompts:hephaestus-network`.
- Cursor command files are plain Markdown with no templating; arguments typed
  after the command are appended to the prompt automatically.
- AGENTS.md-only runtimes still cannot register slash commands — the fallback
  is an instructions file, copied per project.
- Local model runtimes vary; the universal contract is: (1) read AGENTS.md or
  the skill, (2) call `hephaestus route` (shell) or `hephaestus_route` (MCP),
  (3) honor the decision JSON. The router does not execute tools; host runtime
  permissions apply when an agent actually acts.
- If command registration fails anywhere, the terminal form always works:
  `Hephaestus-build "<request>"`, `hephaests-network "<request>"`, or
  `hephaestus cloud "<request>"`.

First-use memory behavior: whichever runtime calls the router first triggers
`network init` (also run by the installer). All later calls from any runtime
reuse the same `~/.agentlas/networking/` — one local memory map, no per-runtime
copies.
