# OpenCode Adapter

OpenCode reads three Hephaestus surfaces — all installed by
`scripts/install-all-runtimes.sh`:

1. **Commands** — `commands/*.md` here are copied to
   `~/.config/opencode/commands/`, giving `/hephaestus` and
   `/hephaestus-network` in the OpenCode TUI.
2. **Skill** — OpenCode natively loads `~/.agents/skills/hephaestus-network/`
   (installed from the canonical `skills/hephaestus-network/`), so routing also
   triggers implicitly via the `skill` tool.
3. **MCP** — for tool-level access (works with any model, including local
   Ollama models), register the stdio server in `opencode.json`:

```json
{
  "mcp": {
    "hephaestus-network": {
      "type": "local",
      "command": ["~/.agentlas/runtime/current/bin/hephaestus", "mcp", "serve"],
      "enabled": true
    }
  }
}
```

Manual install without the one-touch script:

```bash
mkdir -p ~/.config/opencode/commands
cp opencode/commands/*.md ~/.config/opencode/commands/
mkdir -p ~/.agents/skills
cp -R skills/hephaestus-network ~/.agents/skills/
```
