"""Stormbreaker Run Journal.

An append-only step ledger that makes a long-horizon Stormbreaker run survive an
interruption. Every step writes a `start` record, then a terminal `complete` or
`fail` record. If the process dies mid-step, the journal still holds the truth of
what finished, what was in flight, and what looped, so the run can be resumed
from the first unfinished step instead of restarting from zero.

Three failure modes it makes recoverable:

- **Resume after a hard stop** — `resume_plan()` reports the completed steps to
  skip and the first step to re-enter.
- **Dangling step repair** — a step that started but never reached a terminal
  record is detected and can be sealed with a `repair` record so a resumed run
  treats it as retryable instead of silently lost.
- **Loop guard** — a step (by signature) that keeps restarting without ever
  completing trips a hard-stop signal so the run stops burning cycles.

Pure standard library, deterministic, local-first. No model calls.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TERMINAL_EVENTS = ("complete", "fail")
DEFAULT_LOOP_THRESHOLD = 3


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class RunJournal:
    """Append-only JSONL journal for one Stormbreaker run."""

    path: Path

    def __post_init__(self) -> None:
        self.path = Path(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Sequence counter is cached in-memory and initialized from disk once on
        # the first write. Re-reading the whole journal per append would make a
        # long run O(n^2) in its own step count, defeating the point.
        self._seq: int | None = None

    # -- writers ------------------------------------------------------------
    def _append(self, event: str, step_id: str, **fields: Any) -> dict[str, Any]:
        if self._seq is None:
            self._seq = self._count_existing_records()
        self._seq += 1
        record = {"seq": self._seq, "event": event, "step_id": step_id, "ts": _now()}
        record.update({key: value for key, value in fields.items() if value is not None})
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        return record

    def _count_existing_records(self) -> int:
        if not self.path.exists():
            return 0
        with self.path.open("r", encoding="utf-8") as handle:
            return sum(1 for line in handle if line.strip())

    def start_step(self, step_id: str, signature: str | None = None, payload: Any = None) -> dict[str, Any]:
        return self._append("start", step_id, signature=signature or step_id, payload=payload)

    def complete_step(self, step_id: str, result_ref: str | None = None) -> dict[str, Any]:
        return self._append("complete", step_id, result_ref=result_ref)

    def fail_step(self, step_id: str, error: str) -> dict[str, Any]:
        return self._append("fail", step_id, error=error)

    # -- verifier-first ------------------------------------------------------
    def plan_step(self, step_id: str, verifier: str) -> dict[str, Any]:
        """Declare HOW a step will be checked before doing it. The verifier is a
        plain description of the proof that will mark the step trustworthy."""
        return self._append("plan", step_id, verifier=verifier)

    def verify_step(self, step_id: str, passed: bool, evidence: str | None = None) -> dict[str, Any]:
        """Record the verification result for a step. A step that completes
        without a passing verification is reported as `unverified`."""
        return self._append("verify", step_id, passed=bool(passed), evidence=evidence)

    # -- clarification interrupt --------------------------------------------
    def request_clarification(self, step_id: str, question: str) -> dict[str, Any]:
        """Pause on ambiguity instead of guessing. The run is `blocked` while any
        question is open."""
        return self._append("clarify_request", step_id, question=question)

    def resolve_clarification(self, step_id: str, answer: str) -> dict[str, Any]:
        return self._append("clarify_resolve", step_id, answer=answer)

    # -- readers ------------------------------------------------------------
    def events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        events: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                # A torn final line (killed mid-write) is reported by verify();
                # it never silently changes the resume decision.
                events.append({"event": "corrupt", "step_id": "", "raw": line})
        return events

    def _step_states(self) -> tuple[dict[str, dict[str, Any]], list[str]]:
        """Return per-step state plus the first-seen order of step ids."""
        states: dict[str, dict[str, Any]] = {}
        order: list[str] = []
        for event in self.events():
            kind = event.get("event")
            step_id = event.get("step_id") or ""
            if kind == "corrupt" or not step_id:
                continue
            if step_id not in states:
                states[step_id] = {
                    "starts": 0,
                    "last": None,
                    "signature": step_id,
                    "repaired": False,
                    "verifier": None,
                    "verified": None,
                    "open_questions": 0,
                }
                order.append(step_id)
            state = states[step_id]
            if kind == "start":
                state["starts"] += 1
                state["signature"] = event.get("signature", step_id)
                state["last"] = "start"
            elif kind == "repair":
                state["repaired"] = True
                if state["last"] == "start":
                    state["last"] = "repaired"
            elif kind in TERMINAL_EVENTS:
                state["last"] = kind
            elif kind == "plan":
                state["verifier"] = event.get("verifier")
            elif kind == "verify":
                state["verified"] = "pass" if event.get("passed") else "fail"
            elif kind == "clarify_request":
                state["open_questions"] += 1
            elif kind == "clarify_resolve":
                state["open_questions"] = max(0, state["open_questions"] - 1)
        return states, order

    def resume_plan(self, loop_threshold: int = DEFAULT_LOOP_THRESHOLD) -> dict[str, Any]:
        states, order = self._step_states()
        completed = [step for step in order if states[step]["last"] == "complete"]
        failed = [step for step in order if states[step]["last"] == "fail"]
        dangling = [step for step in order if states[step]["last"] in {"start", "repaired"}]
        loops = [
            step
            for step in order
            if states[step]["starts"] >= loop_threshold and states[step]["last"] != "complete"
        ]
        resume_from = next((step for step in order if states[step]["last"] != "complete"), None)
        # Verifier-first: a step that finished without a passing check is not
        # trustworthy yet. Clarification interrupt: open questions block the run.
        unverified = [step for step in completed if states[step]["verified"] != "pass"]
        verify_failed = [step for step in order if states[step]["verified"] == "fail"]
        awaiting_clarification = [step for step in order if states[step]["open_questions"] > 0]
        return {
            "status": "ok",
            "journal": str(self.path),
            "total_steps": len(order),
            "completed": completed,
            "failed": failed,
            "dangling": dangling,
            "loops": loops,
            "hard_stop": bool(loops),
            "resume_from": resume_from,
            "loop_threshold": loop_threshold,
            "unverified": unverified,
            "verify_failed": verify_failed,
            "awaiting_clarification": awaiting_clarification,
            "blocked": bool(awaiting_clarification),
        }

    def final_gate(self, require_verification: bool = True) -> dict[str, Any]:
        """The run cannot be called done while anything is unfinished, looping,
        failed, awaiting an answer, or (by default) completed-but-unverified.
        Returns a single ok/blockers verdict so a caller never claims success
        before the checks pass."""
        plan = self.resume_plan()
        blockers: dict[str, Any] = {}
        if plan["dangling"]:
            blockers["dangling"] = plan["dangling"]
        if plan["loops"]:
            blockers["loops"] = plan["loops"]
        if plan["failed"]:
            blockers["failed"] = plan["failed"]
        if plan["verify_failed"]:
            blockers["verify_failed"] = plan["verify_failed"]
        if plan["awaiting_clarification"]:
            blockers["awaiting_clarification"] = plan["awaiting_clarification"]
        if require_verification and plan["unverified"]:
            blockers["unverified"] = plan["unverified"]
        return {
            "status": "ok",
            "journal": str(self.path),
            "ok": not blockers,
            "require_verification": require_verification,
            "blockers": blockers,
            "completed": plan["completed"],
        }

    def repair_dangling(self, reason: str = "interrupted") -> list[dict[str, Any]]:
        """Seal every dangling step with a repair record so a resumed run treats
        it as retryable rather than lost. Idempotent: already-repaired or
        terminal steps are skipped."""
        states, order = self._step_states()
        repaired: list[dict[str, Any]] = []
        for step in order:
            if states[step]["last"] == "start":
                repaired.append(self._append("repair", step, reason=reason))
        return repaired

    def verify(self) -> dict[str, Any]:
        issues: list[str] = []
        seen_start: set[str] = set()
        for event in self.events():
            kind = event.get("event")
            step_id = event.get("step_id") or ""
            if kind == "corrupt":
                issues.append(f"corrupt journal line: {event.get('raw', '')[:80]}")
                continue
            if kind == "start":
                seen_start.add(step_id)
            elif kind in TERMINAL_EVENTS and step_id not in seen_start:
                issues.append(f"{kind} for {step_id} without a prior start")
        return {"status": "pass" if not issues else "fail", "journal": str(self.path), "issues": issues}


def default_journal_path(project_dir: str | Path, run_id: str) -> Path:
    safe = "".join(ch for ch in str(run_id) if ch.isalnum() or ch in {"-", "_"}) or "run"
    return Path(project_dir).expanduser().resolve() / ".agentlas" / "stormbreaker" / "journal" / f"{safe}.jsonl"
