# Local Models (Ollama · Gemma · DeepSeek · Hermes)

Ollama, Gemma, DeepSeek, and Hermes are models/model-servers, not agent
runtimes — they have no plugin or command system of their own. Hephaestus
reaches them through two universal surfaces installed by
`scripts/install-all-runtimes.sh`:

1. **AgentSkills skill** — `~/.agents/skills/hephaestus-network/SKILL.md` is
   read natively by OpenCode, Crush, Cursor, Codex, OpenClaw, and Hermes Agent,
   regardless of which model they run.
2. **MCP stdio server** — `hephaestus mcp serve` exposes `hephaestus_route` and
   `hephaestus_network_status` as tools for any MCP-capable harness.

## Ollama

Ollama itself ships no agent harness; the supported flow is `ollama launch`
(v0.15+), which configures an existing harness against local models:

```bash
ollama launch opencode   # or: claude / codex / droid
```

The launched harness then picks up the Hephaestus surfaces it already knows
(commands, skills, plugins). Use a model with ≥64k context for routing-heavy
sessions (e.g. `qwen3-coder`, `gemma3`, `deepseek-r1`).

For a raw `POST /api/chat` or OpenAI-compatible agent loop, expose the router
as a function tool:

```json
{
  "type": "function",
  "function": {
    "name": "hephaestus_route",
    "description": "Route a natural-language request to the right local agent/team/plugin. Returns a JSON decision with receipt_id.",
    "parameters": {
      "type": "object",
      "properties": {"request": {"type": "string"}},
      "required": ["request"]
    }
  }
}
```

and implement the call as `~/.agentlas/runtime/current/bin/hephaestus route
"<request>" --runtime ollama`.

## MCP registration per harness

The stdio server command is always the same:
`~/.agentlas/runtime/current/bin/hephaestus mcp serve`

- **OpenCode** (`opencode.json`):
  `"mcp": {"hephaestus-network": {"type": "local", "command": ["~/.agentlas/runtime/current/bin/hephaestus", "mcp", "serve"]}}`
- **Crush** (`crush.json`):
  `"mcp": {"hephaestus-network": {"type": "stdio", "command": "~/.agentlas/runtime/current/bin/hephaestus", "args": ["mcp", "serve"]}}`
- **Goose** (`~/.config/goose/config.yaml`): add an `extensions:` stdio entry
  with the same command and args.
- **Hermes Agent** (`~/.hermes/config.yaml`): see `hermes/README.md`.
- **Cursor** (`~/.cursor/mcp.json`):
  `"mcpServers": {"hephaestus-network": {"command": "~/.agentlas/runtime/current/bin/hephaestus", "args": ["mcp", "serve"]}}`
- **Codex** (`~/.codex/config.toml`):

  ```toml
  [mcp_servers.hephaestus-network]
  command = "~/.agentlas/runtime/current/bin/hephaestus"
  args = ["mcp", "serve"]
  ```

If a harness does not expand `~`, use the absolute home path.

## DeepSeek

DeepSeek ships no first-party CLI (as of June 2026); run it through any harness
above. Gotcha for BYOK harness setups: use the **Anthropic-compatible**
endpoint `https://api.deepseek.com/anthropic` (provider type `anthropic`) —
the OpenAI-compatible type 400s on agent workloads because thinking mode needs
`reasoning_content` echoed back.

## Hermes / Gemma

- Hermes Agent: skill + MCP, see `hermes/README.md`. Hermes requires ≥64k
  context models.
- Gemma has no runtime of its own — run it via Ollama (`ollama launch ...`) or
  any OpenAI-compatible harness; the surfaces above apply unchanged.

## Privacy

The MCP server and the skill follow the same routing contract as
`hephaestus route`: raw prompts never leave the machine, Hub lookup uses
redacted keywords only, and every decision writes a routing receipt. Actual
tool execution follows the host runtime's safety and permission model.
