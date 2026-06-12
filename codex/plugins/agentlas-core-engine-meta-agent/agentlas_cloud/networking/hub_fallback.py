"""Agentlas Hub fallback (MCP-compatible discovery).

Privacy contract:
- the raw prompt is never sent to the Hub — only redacted, normalized tokens;
- the first remote use requires an explicit user approval (cloud_call grant);
- offline machines degrade to the local cache, then to local-only routing.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .approvals import build_approval_request, has_grant
from .bootstrap import append_jsonl, networking_home, read_json, read_jsonl, utc_now
from .memory import redact_tokens

_HUB_TIMEOUT_SECONDS = 6
HUB_TARGET = "agentlas-hub"


def _hub_url(home: Path) -> str:
    config = read_json(home / "config.json", default={}) or {}
    base = str(config.get("hub_url") or "https://agentlas.cloud").rstrip("/")
    return base


def search_hub(
    query_tokens: list[str],
    home: Path | str | None = None,
    approved: bool = False,
) -> dict[str, Any]:
    base = Path(home) if home else networking_home()
    safe_tokens = [token for token in redact_tokens(query_tokens) if token != "[redacted]"]
    redacted_query = " ".join(dict.fromkeys(safe_tokens))[:200]

    if not approved and not has_grant("cloud_call", HUB_TARGET, base):
        return {
            "status": "approval_required",
            "approval_request": build_approval_request(
                ["cloud_call"],
                HUB_TARGET,
                "No local card matched. Searching Agentlas Hub sends the redacted keywords below (never your raw prompt or local memory).",
                payload_preview=redacted_query,
            ),
        }

    url = _hub_url(base) + "/api/mcp/v1"
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "marketplace.search_agents", "arguments": {"q": redacted_query}},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "hephaestus-network-router",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=_HUB_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        cached = [entry for entry in read_jsonl(base / "cache" / "hub-search.jsonl", limit=20)]
        return {
            "status": "offline",
            "detail": str(exc),
            "cached": cached,
            "note": "Hub unreachable — falling back to cached results, then local-only routing.",
        }

    results = _extract_results(payload)
    append_jsonl(
        base / "cache" / "hub-search.jsonl",
        {"ts": utc_now(), "q": redacted_query, "count": len(results), "slugs": [item.get("slug") for item in results[:10]]},
    )
    return {"status": "ok", "query": redacted_query, "results": results}


def _extract_results(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    result = payload.get("result")
    if isinstance(result, dict):
        content = result.get("content")
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    try:
                        parsed = json.loads(item.get("text") or "")
                    except ValueError:
                        continue
                    if isinstance(parsed, dict) and isinstance(parsed.get("results"), list):
                        return [entry for entry in parsed["results"] if isinstance(entry, dict)]
        if isinstance(result.get("results"), list):
            return [entry for entry in result["results"] if isinstance(entry, dict)]
    return []
