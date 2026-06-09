# Agentlas Cloud Runtime Contract

Hephaestus now emits and repairs `agentlas.json` before an agent package is
allowed into Agentlas Cloud call flows.

## V1 Scope

- Generate or repair `agentlas.json`.
- Run local risk screening before private sync or public publish.
- Compile a runtime bundle instead of sending the whole ZIP to an LLM.
- Gate `agentlas.read_agent_file` through `allowRead` and `denyRead`.
- Keep private sync and public clean-copy behavior separate.

## CLI

```bash
bin/hephaestus wizard ./some-agent --name instagram-operator
bin/hephaestus security scan ./some-agent --strict
bin/hephaestus runtime bundle ./some-agent
bin/hephaestus runtime read-agent-file ./some-agent AGENTS.md
bin/hephaestus field-test
```

## Lazy File Read

`runtime bundle` sends the manifest, bounded file index, package hash, and risk
summary first. Full file contents are fetched only through
`runtime read-agent-file`, and only when `agentlas.json` allows the requested
path.

The security scan is risk screening, not a safety guarantee. It reports file
paths, risk types, and redaction status without printing secret values.

## Non-Goals

- Cloud server-side model execution.
- User key or OAuth token storage.
- Vault snapshot upload.
- Web-based agent editing.
- Enterprise policy implementation.
