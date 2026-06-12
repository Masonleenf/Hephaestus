"""Routing memory: structured preferences and corrections only.

Hard rules:
- never store raw prompts, secrets, file contents, or transcripts;
- feedback adjusts a user-local boost/suppression profile only — it can never
  promote a card's routing_status (that requires lint + benchmarks), so bad
  routes cannot be reinforced into the shared card inventory.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .bootstrap import append_jsonl, atomic_write_json, networking_home, read_json, utc_now

SECRET_PATTERNS = [
    re.compile(r"sk-[a-z0-9]{8,}", re.IGNORECASE),
    re.compile(r"akia[0-9a-z]{12,}", re.IGNORECASE),
    re.compile(r"ghp_[a-z0-9]{20,}", re.IGNORECASE),
    re.compile(r"xox[baprs]-[a-z0-9-]{8,}", re.IGNORECASE),
    re.compile(r"-----begin", re.IGNORECASE),
    re.compile(r"(api[_-]?key|password|passwd|secret|token)\s*[:=]", re.IGNORECASE),
]

BOOST_LIMIT = 3.0
CORRECTIONS_LIMIT = 200


def redact_tokens(tokens: list[str]) -> list[str]:
    safe: list[str] = []
    for token in tokens:
        if any(pattern.search(token) for pattern in SECRET_PATTERNS):
            safe.append("[redacted]")
        else:
            safe.append(token)
    return safe


def contains_secret(text: str) -> bool:
    return any(pattern.search(text or "") for pattern in SECRET_PATTERNS)


def load_profile(home: Path | str | None = None) -> dict[str, Any]:
    base = Path(home) if home else networking_home()
    return read_json(base / "memory" / "routing-profile.json", default={"boosts": {}, "suppressions": {}, "corrections": []})


def profile_adjustment(profile: dict[str, Any], card_id: str) -> float:
    boost = float((profile.get("boosts") or {}).get(card_id, 0.0))
    suppression = float((profile.get("suppressions") or {}).get(card_id, 0.0))
    return max(-BOOST_LIMIT, min(BOOST_LIMIT, boost - suppression))


def record_feedback(
    query_tokens: list[str],
    chosen_card: str | None,
    correct_card: str | None,
    home: Path | str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    base = Path(home) if home else networking_home()
    tokens = redact_tokens(query_tokens)
    append_jsonl(
        base / "memory" / "feedback.jsonl",
        {"ts": utc_now(), "tokens": tokens, "chosen": chosen_card, "correct": correct_card, "note": note},
    )
    profile = load_profile(base)
    boosts = profile.setdefault("boosts", {})
    suppressions = profile.setdefault("suppressions", {})
    if correct_card:
        boosts[correct_card] = min(BOOST_LIMIT, float(boosts.get(correct_card, 0.0)) + 0.5)
    if chosen_card and chosen_card != correct_card:
        suppressions[chosen_card] = min(BOOST_LIMIT, float(suppressions.get(chosen_card, 0.0)) + 0.5)
    corrections = profile.setdefault("corrections", [])
    corrections.append({"ts": utc_now(), "tokens": tokens[:12], "correct": correct_card, "chosen": chosen_card})
    profile["corrections"] = corrections[-CORRECTIONS_LIMIT:]
    atomic_write_json(Path(base) / "memory" / "routing-profile.json", profile)
    return {"status": "recorded", "boosts": boosts.get(correct_card) if correct_card else None}
