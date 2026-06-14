"""Local Agentlas OAuth helper for Hephaestus runtimes.

The public Hub supports standard OAuth metadata. This module turns that into a
first-run browser sign-in for local runtimes, then keeps the refresh token in a
local Agentlas auth store so Claude Code, Codex, Gemini, and other MCP hosts can
reuse the same session without teaching users what a session token is.
"""

from __future__ import annotations

import base64
import hashlib
import http.server
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from typing import Any

DEFAULT_AGENTLAS_URL = "https://agentlas.cloud"
TOKEN_REFRESH_SKEW_SECONDS = 60
LOGIN_TIMEOUT_SECONDS = 180


class AgentlasAuthError(RuntimeError):
    """Raised when the local OAuth flow cannot complete safely."""


def normalize_base_url(base_url: str | None = None) -> str:
    return (base_url or os.environ.get("AGENTLAS_HUB_URL") or DEFAULT_AGENTLAS_URL).rstrip("/")


def auth_home() -> Path:
    configured = os.environ.get("AGENTLAS_AUTH_HOME")
    if configured:
        base = Path(configured).expanduser()
    else:
        agentlas_home = Path(os.environ.get("AGENTLAS_HOME") or (Path.home() / ".agentlas")).expanduser()
        base = agentlas_home / "auth"
    base.mkdir(parents=True, exist_ok=True)
    try:
        base.chmod(0o700)
    except OSError:
        pass
    return base


def token_path(base_url: str | None = None) -> Path:
    parsed = urllib.parse.urlparse(normalize_base_url(base_url))
    host = (parsed.netloc or "agentlas").replace(":", "_")
    return auth_home() / f"{host}.json"


def read_token_record(base_url: str | None = None) -> dict[str, Any] | None:
    path = token_path(base_url)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


def write_token_record(record: dict[str, Any], base_url: str | None = None) -> Path:
    path = token_path(base_url or str(record.get("base_url") or ""))
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        tmp.chmod(0o600)
    except OSError:
        pass
    tmp.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return path


def delete_token_record(base_url: str | None = None) -> bool:
    path = token_path(base_url)
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False


def auth_status(base_url: str | None = None) -> dict[str, Any]:
    base = normalize_base_url(base_url)
    record = read_token_record(base)
    if not record:
        return {"status": "signed_out", "base_url": base, "token_path": str(token_path(base))}
    now = int(time.time())
    expires_at = int(record.get("expires_at") or 0)
    has_access = bool(record.get("access_token")) and expires_at > now + TOKEN_REFRESH_SKEW_SECONDS
    has_refresh = bool(record.get("refresh_token")) and bool(record.get("client_id"))
    return {
        "status": "authenticated" if has_access else ("refreshable" if has_refresh else "expired"),
        "base_url": base,
        "token_path": str(token_path(base)),
        "expires_at": expires_at or None,
        "has_refresh_token": has_refresh,
    }


def ensure_access_token(
    base_url: str | None = None,
    *,
    interactive: bool = False,
    open_browser: bool = True,
    timeout_seconds: int = LOGIN_TIMEOUT_SECONDS,
) -> str | None:
    """Return a usable Bearer token, refreshing or opening a browser if allowed."""

    base = normalize_base_url(base_url)
    record = read_token_record(base)
    token = _valid_access_token(record)
    if token:
        return token
    if record and record.get("refresh_token") and record.get("client_id"):
        refreshed = _refresh_token(base, record)
        if refreshed:
            return str(refreshed["access_token"])
    if not interactive:
        return None
    login_result = login(base, open_browser=open_browser, timeout_seconds=timeout_seconds)
    return str(login_result["access_token"])


def login(
    base_url: str | None = None,
    *,
    open_browser: bool = True,
    timeout_seconds: int = LOGIN_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Run Authorization Code + PKCE through the user's default browser."""

    base = normalize_base_url(base_url)
    metadata = _fetch_metadata(base)
    server = _CallbackServer(("127.0.0.1", 0), _OAuthCallbackHandler)
    redirect_uri = f"http://127.0.0.1:{server.server_port}/callback"
    client_id = _register_client(metadata["registration_endpoint"], redirect_uri)
    verifier = _code_verifier()
    challenge = _code_challenge(verifier)
    state = secrets.token_urlsafe(24)
    auth_url = _authorization_url(
        metadata["authorization_endpoint"],
        client_id=client_id,
        redirect_uri=redirect_uri,
        state=state,
        code_challenge=challenge,
    )
    server.expected_state = state
    opened = False
    if open_browser:
        opened = bool(webbrowser.open(auth_url, new=1, autoraise=True))
    _wait_for_callback(server, timeout_seconds)
    if server.error:
        raise AgentlasAuthError(server.error)
    if not server.code:
        raise AgentlasAuthError("Timed out waiting for browser sign-in to finish.")

    tokens = _exchange_code(
        metadata["token_endpoint"],
        code=server.code,
        client_id=client_id,
        redirect_uri=redirect_uri,
        code_verifier=verifier,
    )
    record = _token_record(base, metadata, client_id, tokens)
    path = write_token_record(record, base)
    return {
        "status": "authenticated",
        "base_url": base,
        "opened_browser": opened,
        "authorization_url": auth_url if not opened else None,
        "token_path": str(path),
        "expires_at": record.get("expires_at"),
        "access_token": record["access_token"],
    }


def logout(base_url: str | None = None) -> dict[str, Any]:
    base = normalize_base_url(base_url)
    removed = delete_token_record(base)
    return {"status": "signed_out", "base_url": base, "removed": removed, "token_path": str(token_path(base))}


def bearer_header(base_url: str | None = None, *, interactive: bool = False) -> dict[str, str]:
    token = ensure_access_token(base_url, interactive=interactive)
    return {"Authorization": f"Bearer {token}"} if token else {}


def _valid_access_token(record: dict[str, Any] | None) -> str | None:
    if not record:
        return None
    expires_at = int(record.get("expires_at") or 0)
    if not record.get("access_token") or expires_at <= int(time.time()) + TOKEN_REFRESH_SKEW_SECONDS:
        return None
    return str(record["access_token"])


def _fetch_metadata(base_url: str) -> dict[str, Any]:
    url = f"{base_url}/.well-known/oauth-authorization-server"
    payload = _json_request(url, method="GET")
    required = ("authorization_endpoint", "token_endpoint", "registration_endpoint")
    missing = [key for key in required if not payload.get(key)]
    if missing:
        raise AgentlasAuthError(f"Agentlas OAuth metadata is missing: {', '.join(missing)}")
    return payload


def _register_client(registration_endpoint: str, redirect_uri: str) -> str:
    payload = _json_request(
        registration_endpoint,
        method="POST",
        data={
            "client_name": "Hephaestus Network",
            "redirect_uris": [redirect_uri],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        },
    )
    client_id = str(payload.get("client_id") or "")
    if not client_id:
        raise AgentlasAuthError("Agentlas OAuth registration did not return a client_id.")
    return client_id


def _refresh_token(base_url: str, record: dict[str, Any]) -> dict[str, Any] | None:
    try:
        tokens = _token_request(
            str(record["token_endpoint"]),
            {
                "grant_type": "refresh_token",
                "refresh_token": str(record["refresh_token"]),
                "client_id": str(record["client_id"]),
            },
        )
    except AgentlasAuthError:
        return None
    refreshed = {
        **record,
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token") or record.get("refresh_token"),
        "token_type": tokens.get("token_type") or record.get("token_type") or "Bearer",
        "scope": tokens.get("scope") or record.get("scope") or "mcp",
        "expires_at": int(time.time()) + int(tokens.get("expires_in") or 0),
        "updated_at": int(time.time()),
    }
    write_token_record(refreshed, base_url)
    return refreshed


def _exchange_code(
    token_endpoint: str,
    *,
    code: str,
    client_id: str,
    redirect_uri: str,
    code_verifier: str,
) -> dict[str, Any]:
    return _token_request(
        token_endpoint,
        {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        },
    )


def _token_request(token_endpoint: str, params: dict[str, str]) -> dict[str, Any]:
    payload = _json_request(
        token_endpoint,
        method="POST",
        body=urllib.parse.urlencode(params).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
    )
    if not payload.get("access_token"):
        raise AgentlasAuthError("Agentlas OAuth token response did not include an access_token.")
    return payload


def _json_request(
    url: str,
    *,
    method: str,
    data: dict[str, Any] | None = None,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 20,
) -> dict[str, Any]:
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json", **(headers or {})}
    request = urllib.request.Request(url, data=body, headers=headers or {"Accept": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            parsed = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = _safe_http_error_detail(exc)
        raise AgentlasAuthError(f"Agentlas OAuth request failed ({exc.code}): {detail}") from exc
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        raise AgentlasAuthError(f"Agentlas OAuth request failed: {exc}") from exc
    if not isinstance(parsed, dict):
        raise AgentlasAuthError("Agentlas OAuth response was not a JSON object.")
    if parsed.get("error"):
        raise AgentlasAuthError(str(parsed.get("error_description") or parsed.get("error")))
    return parsed


def _safe_http_error_detail(exc: urllib.error.HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8")
    except Exception:
        return exc.reason or "HTTP error"
    try:
        parsed = json.loads(body)
    except ValueError:
        return body[:200]
    return str(parsed.get("error_description") or parsed.get("error") or exc.reason or "HTTP error")[:200]


def _authorization_url(endpoint: str, *, client_id: str, redirect_uri: str, state: str, code_challenge: str) -> str:
    query = urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "scope": "mcp",
        }
    )
    return f"{endpoint}?{query}"


def _code_verifier() -> str:
    return secrets.token_urlsafe(64)


def _code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _token_record(base_url: str, metadata: dict[str, Any], client_id: str, tokens: dict[str, Any]) -> dict[str, Any]:
    now = int(time.time())
    return {
        "schema": "agentlas-oauth-v1",
        "base_url": base_url,
        "client_id": client_id,
        "authorization_endpoint": metadata["authorization_endpoint"],
        "token_endpoint": metadata["token_endpoint"],
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token"),
        "token_type": tokens.get("token_type") or "Bearer",
        "scope": tokens.get("scope") or "mcp",
        "expires_at": now + int(tokens.get("expires_in") or 0),
        "updated_at": now,
    }


class _CallbackServer(http.server.HTTPServer):
    expected_state: str | None = None
    code: str | None = None
    error: str | None = None


class _OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        state = (params.get("state") or [""])[0]
        code = (params.get("code") or [""])[0]
        error = (params.get("error_description") or params.get("error") or [""])[0]
        server = self.server
        assert isinstance(server, _CallbackServer)
        if parsed.path != "/callback":
            self._reply("Agentlas sign-in callback is running. You can close this tab.", status=404)
            return
        if error:
            server.error = error
            self._reply("Agentlas sign-in was cancelled or failed. You can close this tab.", status=400)
            return
        if not code or state != server.expected_state:
            server.error = "Agentlas sign-in callback was invalid."
            self._reply("Agentlas sign-in callback was invalid. You can close this tab.", status=400)
            return
        server.code = code
        self._reply("Agentlas sign-in is complete. You can close this tab and return to your AI app.")

    def _reply(self, body: str, status: int = 200) -> None:
        encoded = (
            "<!doctype html><meta charset='utf-8'>"
            "<title>Agentlas sign-in</title>"
            f"<p style='font:16px system-ui'>{body}</p>"
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def _wait_for_callback(server: _CallbackServer, timeout_seconds: int) -> None:
    deadline = time.time() + max(5, timeout_seconds)
    while time.time() < deadline and not server.code and not server.error:
        server.timeout = max(0.1, min(1.0, deadline - time.time()))
        server.handle_request()
    server.server_close()
