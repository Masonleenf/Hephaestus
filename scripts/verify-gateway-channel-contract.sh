#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

python3 - <<'PY'
import json
import re
from pathlib import Path

schema_path = Path("schemas/gateway-channel.schema.json")
template_path = Path("templates/gateway-channel.json.tpl")
doc_path = Path("docs/hephaestus-agentlas-gateway-architecture.md")
apply_note_path = Path("../../agentlas/AgentsAtlas/app/docs/HEPHAESTUS_AGENTLAS_GATEWAY_APPLY_2026-07-04.md")

for path in (schema_path, template_path, doc_path):
    if not path.exists():
        raise SystemExit(f"missing gateway contract artifact: {path}")

schema = json.loads(schema_path.read_text(encoding="utf-8"))
template = json.loads(template_path.read_text(encoding="utf-8"))
doc = doc_path.read_text(encoding="utf-8")

if schema.get("properties", {}).get("schemaVersion", {}).get("const") != "agentlas.gateway-channel.v1":
    raise SystemExit("gateway schema must pin schemaVersion to agentlas.gateway-channel.v1")

defs = schema.get("$defs", {})
for required_def in [
    "credentialRef",
    "channel",
    "account",
    "accessPolicy",
    "commandPolicy",
    "binding",
    "setupExperience",
    "deliveryDefaults",
    "securityDefaults",
]:
    if required_def not in defs:
        raise SystemExit(f"gateway schema missing $defs.{required_def}")

credential_source = defs["credentialRef"]["properties"]["source"]["enum"]
for source in ["env", "local_vault", "agentlas_vault", "host_secret", "manual"]:
    if source not in credential_source:
        raise SystemExit(f"gateway credentialRef missing source: {source}")

dm_policy = defs["accessPolicy"]["properties"]["dmPolicy"]["enum"]
for policy in ["pairing", "allowlist", "open", "disabled"]:
    if policy not in dm_policy:
        raise SystemExit(f"gateway accessPolicy.dmPolicy missing option: {policy}")

group_policy = defs["accessPolicy"]["properties"]["groupPolicy"]["enum"]
for policy in ["allowlist", "open", "disabled"]:
    if policy not in group_policy:
        raise SystemExit(f"gateway accessPolicy.groupPolicy missing option: {policy}")

if template.get("schemaVersion") != "agentlas.gateway-channel.v1":
    raise SystemExit("gateway template schemaVersion mismatch")

channel = template["channels"]["{{CHANNEL_ID}}"]
account = channel["accounts"]["default"]
if account["access"]["dmPolicy"] != "pairing":
    raise SystemExit("gateway template must default DM access to pairing")
if account["access"]["groupPolicy"] != "allowlist":
    raise SystemExit("gateway template must default group access to allowlist")
if template["security"]["storeRawMessageBodies"] is not False:
    raise SystemExit("gateway template must not store raw message bodies by default")
if "botToken" not in account["credentials"]:
    raise SystemExit("gateway template must include a value-free botToken credential reference")
if "send_test_message" not in template.get("setup", {}).get("steps", []):
    raise SystemExit("gateway template setup must include a test message step")
if "confirm_receipt" not in template.get("setup", {}).get("steps", []):
    raise SystemExit("gateway template setup must require delivery receipt confirmation")

for needle in [
    "Hermes",
    "OpenClaw",
    "Telegram",
    "Slack",
    "pairing",
    "Binding",
    "receipt",
    "UX",
    "test message",
    "schemas/gateway-channel.schema.json",
]:
    if needle not in doc:
        raise SystemExit(f"gateway architecture doc missing required reference: {needle}")

if apply_note_path.exists():
    apply_note = apply_note_path.read_text(encoding="utf-8")
    for needle in [
        "gateway_configs",
        "gateway_bindings",
        "gateway_pairing_requests",
        "gateway_delivery_receipts",
        "agentlas.propose_gateway_config",
        "agentlas.decide_gateway_config",
    ]:
        if needle not in apply_note:
            raise SystemExit(f"Agentlas Web gateway apply note missing: {needle}")

public_text = "\n".join([
    schema_path.read_text(encoding="utf-8"),
    template_path.read_text(encoding="utf-8"),
    doc,
])

token_like_patterns = [
    r"xox[baprs]-[A-Za-z0-9-]{20,}",
    r"\b[0-9]{8,}:[A-Za-z0-9_-]{25,}\b",
]
for pattern in token_like_patterns:
    match = re.search(pattern, public_text)
    if match:
        raise SystemExit(f"gateway contract contains a token-like value: {match.group(0)[:12]}...")

print("Gateway channel contract verification passed.")
PY
