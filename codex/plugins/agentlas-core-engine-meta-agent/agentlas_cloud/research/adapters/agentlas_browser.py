"""Agentlas Browser engine adapter.

Drives the user's own `agentlas-browser` launcher (a dependency-free node script that
opens a dedicated logged-in Chrome profile over CDP, attaches @playwright/mcp, and layers
an approval gate + learn-and-replay skills) over MCP stdio. No third-party browser binary.

The launcher .mjs is bundled next to this module and materialized to
``~/.agentlas/agentlas-browser-cdp.mjs`` on first use, so a standalone Hephaestus (no
desktop app) is fully self-contained. When the Agentlas desktop app is present on the same
machine they share ``~/.agentlas`` (profile, skills, approval server) automatically.
"""

from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from agentlas_cloud.networking.bootstrap import utc_now

from ..contracts import ResearchAttempt, ResearchResult, _stable_hash
from ..policy import classify_url

BUNDLED_LAUNCHER = Path(__file__).with_name("agentlas_browser_launcher.mjs")


def launcher_path() -> Path:
    return Path(os.path.expanduser("~")) / ".agentlas" / "agentlas-browser-cdp.mjs"


def materialize_launcher() -> Path:
    """Copy the bundled launcher to ~/.agentlas if missing or out of date (idempotent)."""
    dest = launcher_path()
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        src_bytes = BUNDLED_LAUNCHER.read_bytes() if BUNDLED_LAUNCHER.exists() else b""
        cur = dest.read_bytes() if dest.exists() else None
        if src_bytes and cur != src_bytes:
            dest.write_bytes(src_bytes)
    except OSError:
        pass
    return dest


class _McpSession:
    """Minimal synchronous MCP stdio client for the agentlas-browser launcher."""

    def __init__(self, *, timeout: int = 60, extra_env: dict[str, str] | None = None):
        self.timeout = timeout
        self._id = 0
        self._q: "queue.Queue[dict]" = queue.Queue()
        launcher = materialize_launcher()
        node = shutil.which("node") or "node"
        env = dict(os.environ)
        if extra_env:
            env.update(extra_env)
        self.proc = subprocess.Popen(
            [node, str(launcher)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=env,
            text=True,
            bufsize=1,
        )
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def _read_loop(self) -> None:
        assert self.proc.stdout is not None
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                self._q.put(json.loads(line))
            except json.JSONDecodeError:
                continue

    def _send(self, obj: dict) -> None:
        assert self.proc.stdin is not None
        self.proc.stdin.write(json.dumps(obj) + "\n")
        self.proc.stdin.flush()

    def _await_id(self, want: int) -> dict:
        import time

        deadline = time.time() + self.timeout
        while time.time() < deadline:
            try:
                msg = self._q.get(timeout=max(0.1, deadline - time.time()))
            except queue.Empty:
                break
            if msg.get("id") == want:
                return msg
            # ignore notifications / other ids
        raise TimeoutError("agentlas-browser MCP call timed out")

    def initialize(self) -> None:
        self._id += 1
        self._send({
            "jsonrpc": "2.0",
            "id": self._id,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "hephaestus", "version": "0"}},
        })
        self._await_id(self._id)
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict:
        self._id += 1
        mid = self._id
        self._send({"jsonrpc": "2.0", "id": mid, "method": "tools/call", "params": {"name": name, "arguments": arguments}})
        return self._await_id(mid)

    def close(self) -> None:
        try:
            if self.proc.stdin:
                self.proc.stdin.close()
        except OSError:
            pass
        try:
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass


def _text_of(result: dict) -> str:
    content = (result or {}).get("result", {}).get("content") or []
    parts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
    return "\n".join(p for p in parts if p).strip()


def _is_error(result: dict) -> bool:
    r = (result or {}).get("result") or {}
    return bool(r.get("isError")) or bool((result or {}).get("error"))


class AgentlasBrowserAdapter:
    """hep-browser engine backed by the user's agentlas-browser launcher (MCP)."""

    module_id = "browser.agentlas"
    capabilities = ("browser.snapshot", "browser.automation", "read.url", "browser.skill")
    weight = "browser_heavy"

    def __init__(self, *, timeout_seconds: int = 60, home: Path | str | None = None):
        self.timeout_seconds = timeout_seconds
        self.home = Path(home) if home else None

    def _session(self) -> _McpSession:
        s = _McpSession(timeout=self.timeout_seconds)
        s.initialize()
        return s

    def read(self, source_hint: str, request: Any) -> tuple[ResearchResult | None, ResearchAttempt]:
        safe, reason = classify_url(source_hint)
        if not safe:
            return (
                ResearchResult.blocked(source_hint, reason=f"ssrf_blocked:{reason}"),
                ResearchAttempt(self.module_id, "blocked", f"ssrf_blocked:{reason}", source_hint, weight=self.weight),
            )
        s = None
        try:
            s = self._session()
            nav = s.call_tool("browser_navigate", {"url": source_hint})
            if _is_error(nav):
                return None, ResearchAttempt(self.module_id, "error", "navigate_failed", source_hint, weight=self.weight)
            snap = s.call_tool("browser_snapshot", {})
            text = _text_of(snap)
        except TimeoutError:
            return None, ResearchAttempt(self.module_id, "error", "timeout", source_hint, weight=self.weight)
        except OSError as exc:
            return None, ResearchAttempt(self.module_id, "error", str(exc), source_hint, weight=self.weight)
        finally:
            if s:
                s.close()
        if not text:
            return None, ResearchAttempt(self.module_id, "error", "empty_snapshot", source_hint, weight=self.weight)
        result = ResearchResult(
            source_id=_stable_hash(source_hint),
            url=source_hint,
            title=source_hint,
            platform="browser",
            content_markdown=text,
            extracted_at=utc_now(),
            freshness=getattr(request, "freshness", None),
            confidence="usable",
            limits=["agentlas_browser", "dedicated_profile"],
            citations=[{"label": source_hint, "url": source_hint}],
        )
        return result, ResearchAttempt(self.module_id, "ok", "snapshot", source_hint, weight=self.weight)

    def run_actions(
        self,
        source_hint: str,
        actions: list[dict[str, str]],
        *,
        browser_args: list[str] | None = None,
        keep_open: bool = False,
        wait_ms: int = 0,
    ) -> dict[str, Any]:
        safe, reason = classify_url(source_hint)
        if not safe:
            return {"status": "blocked", "reason": f"ssrf_blocked:{reason}", "url": source_hint, "module": self.module_id, "steps": []}
        steps: list[dict[str, Any]] = []
        s = None
        try:
            s = self._session()
            nav = s.call_tool("browser_navigate", {"url": source_hint})
            steps.append({"label": "navigate", "isError": _is_error(nav)})
            for i, action in enumerate(actions or []):
                atype = str(action.get("type") or "").strip()
                target = str(action.get("target") or "").strip()
                if atype in ("find_text_click", "click_text"):
                    resp = s.call_tool("browser_click", {"element": target, "ref": target})
                elif atype == "click":
                    resp = s.call_tool("browser_click", {"element": target, "ref": target})
                elif atype == "type":
                    resp = s.call_tool("browser_type", {"element": target, "text": str(action.get("text") or "")})
                else:
                    steps.append({"label": f"skip:{atype}", "isError": True})
                    continue
                steps.append({"label": f"{atype}:{i+1}", "isError": _is_error(resp)})
            snap = s.call_tool("browser_snapshot", {})
            snapshot_text = _text_of(snap)
        except TimeoutError:
            return {"status": "error", "reason": "timeout", "url": source_hint, "module": self.module_id, "steps": steps}
        finally:
            if s:
                s.close()
        status = "ok" if all(not st.get("isError") for st in steps) else "error"
        return {"status": status, "url": source_hint, "module": self.module_id, "engine": "agentlas-browser", "steps": steps, "snapshot": snapshot_text}

    def automate(
        self,
        source_hint: str,
        instruction: str,
        *,
        browser_args: list[str] | None = None,
        keep_open: bool = False,
    ) -> dict[str, Any]:
        """NL automation. The agentlas-browser engine has no inline LLM, so:
          - if the instruction names a saved skill (or `replay:<name>`) → replay it deterministically;
          - otherwise navigate + snapshot and hand back to the host LLM (which can drive the MCP
            tools and then call browser_skill_save to learn the task once).
        """
        safe, reason = classify_url(source_hint)
        if not safe:
            return {"status": "blocked", "reason": f"ssrf_blocked:{reason}", "url": source_hint, "module": self.module_id, "steps": []}
        instr = (instruction or "").strip()
        want = instr[len("replay:"):].strip() if instr.lower().startswith("replay:") else instr
        s = None
        try:
            s = self._session()
            skills = []
            try:
                skills = json.loads(_text_of(s.call_tool("browser_skill_list", {})))
            except (json.JSONDecodeError, ValueError):
                skills = []
            if want in skills:
                resp = s.call_tool("browser_skill_replay", {"name": want})
                return {"status": "error" if _is_error(resp) else "ok", "mode": "skill_replay", "module": self.module_id, "skill": want, "detail": _text_of(resp)}
            nav = s.call_tool("browser_navigate", {"url": source_hint})
            snap = s.call_tool("browser_snapshot", {})
            return {
                "status": "needs_host_llm",
                "reason": "Natural-language automation needs the host LLM to drive the MCP browser tools, or a saved skill. Explore via the tools, then call browser_skill_save to learn it once.",
                "module": self.module_id,
                "engine": "agentlas-browser",
                "url": source_hint,
                "navigate_error": _is_error(nav),
                "available_skills": skills,
                "snapshot": _text_of(snap),
            }
        except TimeoutError:
            return {"status": "error", "reason": "timeout", "url": source_hint, "module": self.module_id, "steps": []}
        finally:
            if s:
                s.close()

    # ── learn-and-replay skills ────────────────────────────────────
    def replay_skill(self, name: str) -> dict[str, Any]:
        s = None
        try:
            s = self._session()
            resp = s.call_tool("browser_skill_replay", {"name": name})
            return {"status": "error" if _is_error(resp) else "ok", "module": self.module_id, "skill": name, "detail": _text_of(resp)}
        except TimeoutError:
            return {"status": "error", "reason": "timeout", "module": self.module_id, "skill": name}
        finally:
            if s:
                s.close()

    def list_skills(self) -> list[str]:
        s = None
        try:
            s = self._session()
            resp = s.call_tool("browser_skill_list", {})
            try:
                return json.loads(_text_of(resp))
            except (json.JSONDecodeError, ValueError):
                return []
        except TimeoutError:
            return []
        finally:
            if s:
                s.close()
