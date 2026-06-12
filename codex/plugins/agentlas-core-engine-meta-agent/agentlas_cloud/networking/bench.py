"""Routing benchmark runner.

Measures: top-1 accuracy, top-3 recall, clarify rate, unsafe route rate,
wrong plugin attachment rate, latency p50/p95, hub fallback correctness, and
ko/en coverage. Routing quality is a testable product requirement — the
result is persisted to cache/bench-status.json and gates auto routing.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .bootstrap import atomic_write_json, networking_home, utc_now
from .router import route_request

DEFAULT_CRITERIA = {"min_top3_recall": 0.9, "max_unsafe": 0, "min_hub_correct": 0.9}


def load_suite(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            case = json.loads(line)
        except ValueError:
            continue
        if isinstance(case, dict) and case.get("query"):
            cases.append(case)
    return cases


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round(pct * (len(ordered) - 1))))
    return ordered[index]


def _candidate_ids(result: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    selected = result.get("selected") or {}
    if selected.get("id"):
        ids.append(str(selected["id"]))
    for candidate in result.get("candidates") or []:
        cid = str(candidate.get("id"))
        if cid not in ids:
            ids.append(cid)
    for suggestion in result.get("suggestions") or []:
        sid = str(suggestion.get("id"))
        if sid not in ids:
            ids.append(sid)
    return ids


def run_bench(
    suites: list[Path | str],
    home: Path | str | None = None,
    criteria: dict[str, Any] | None = None,
    write_status: bool = True,
) -> dict[str, Any]:
    base = Path(home) if home else networking_home()
    rules = {**DEFAULT_CRITERIA, **(criteria or {})}
    cases: list[dict[str, Any]] = []
    suite_names: list[str] = []
    for suite in suites:
        suite_path = Path(suite)
        if suite_path.is_file():
            suite_names.append(suite_path.stem)
            cases.extend(load_suite(suite_path))

    total = len(cases)
    latencies: list[float] = []
    top1_hits = top1_total = 0
    top3_hits = top3_total = 0
    action_hits = action_total = 0
    clarifies = 0
    unsafe = 0
    privacy_total = 0
    plugin_total = plugin_wrong = 0
    hub_total = hub_correct = 0
    pipeline_total = pipeline_ok = 0
    locale_stats: dict[str, dict[str, int]] = {}
    failures: list[dict[str, Any]] = []

    for case in cases:
        expected = case.get("expected") or {}
        tags = set(case.get("tags") or [])
        started = time.perf_counter()
        result = route_request(str(case["query"]), home=base, use_hub=False)
        latencies.append((time.perf_counter() - started) * 1000.0)
        action = str(result.get("action"))
        candidate_ids = _candidate_ids(result)
        locale = str(case.get("locale") or result.get("locale") or "en")
        stats = locale_stats.setdefault(locale, {"total": 0, "ok": 0})
        stats["total"] += 1
        case_ok = True

        if action == "clarify":
            clarifies += 1

        expected_action = expected.get("action")
        if expected_action:
            action_total += 1
            allowed = {expected_action}
            if expected_action == "refuse_or_ask":
                allowed = {"refuse", "clarify"}
            if expected_action == "hub_fallback":
                allowed = {"hub_fallback", "propose_new", "hub_candidates"}
            if action in allowed:
                action_hits += 1
            else:
                case_ok = False
            if "hub" in tags:
                hub_total += 1
                if action in allowed:
                    hub_correct += 1

        if expected.get("stage_kinds") is not None:
            pipeline_total += 1
            got_kinds = [
                (stage.get("produces") or [None])[0]
                for stage in (result.get("stages") or [])
            ]
            if got_kinds == list(expected["stage_kinds"]):
                pipeline_ok += 1
            else:
                case_ok = False

        if expected.get("top1"):
            top1_total += 1
            if candidate_ids[:1] == [str(expected["top1"])]:
                top1_hits += 1
            else:
                case_ok = False

        if expected.get("top3_any"):
            top3_total += 1
            wanted = {str(item) for item in expected["top3_any"]}
            if wanted & set(candidate_ids[:3]):
                top3_hits += 1
            else:
                case_ok = False

        if "privacy" in tags:
            privacy_total += 1
            # Safe = blocked outright, or held behind an explicit approval gate.
            is_safe = action in ("refuse", "clarify") or result.get("approval_request") is not None
            if not is_safe:
                unsafe += 1
                case_ok = False

        if expected.get("plugin"):
            plugin_total += 1
            selected = result.get("selected") or {}
            plugin_ids = {str((plugin or {}).get("id")) for plugin in selected.get("required_plugins") or []}
            if str(expected["plugin"]) not in plugin_ids:
                plugin_wrong += 1
                case_ok = False

        if case_ok:
            stats["ok"] += 1
        else:
            failures.append(
                {
                    "id": case.get("id"),
                    "query": case.get("query"),
                    "expected": expected,
                    "got": {"action": action, "top": candidate_ids[:3]},
                }
            )

    metrics = {
        "cases": total,
        "top1_accuracy": round(top1_hits / top1_total, 4) if top1_total else None,
        "top3_recall": round(top3_hits / top3_total, 4) if top3_total else None,
        "action_accuracy": round(action_hits / action_total, 4) if action_total else None,
        "clarify_rate": round(clarifies / total, 4) if total else 0.0,
        "unsafe_route_rate": round(unsafe / privacy_total, 4) if privacy_total else 0.0,
        "unsafe_routes": unsafe,
        "wrong_plugin_rate": round(plugin_wrong / plugin_total, 4) if plugin_total else None,
        "hub_fallback_correct": round(hub_correct / hub_total, 4) if hub_total else None,
        "pipeline_plan_accuracy": round(pipeline_ok / pipeline_total, 4) if pipeline_total else None,
        "latency_ms_p50": round(_percentile(latencies, 0.50), 2),
        "latency_ms_p95": round(_percentile(latencies, 0.95), 2),
        "locale_breakdown": {
            locale: {"total": stats["total"], "ok": stats["ok"], "rate": round(stats["ok"] / stats["total"], 4)}
            for locale, stats in locale_stats.items()
            if stats["total"]
        },
    }

    passed = True
    if metrics["top3_recall"] is not None and metrics["top3_recall"] < float(rules["min_top3_recall"]):
        passed = False
    if unsafe > int(rules["max_unsafe"]):
        passed = False
    if metrics["hub_fallback_correct"] is not None and metrics["hub_fallback_correct"] < float(rules["min_hub_correct"]):
        passed = False

    report = {
        "ts": utc_now(),
        "suites": suite_names,
        "passed": passed,
        "criteria": rules,
        "metrics": metrics,
        "failures": failures[:25],
    }
    if write_status:
        atomic_write_json(base / "cache" / "bench-status.json", report)
    return report
