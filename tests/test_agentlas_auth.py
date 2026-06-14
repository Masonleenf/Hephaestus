import json
import urllib.parse

from agentlas_cloud.auth import auth_status, ensure_access_token, token_path, write_token_record
from agentlas_cloud.networking.hub_client import call_hub_tool


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_refresh_token_is_silent_and_local_only(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTLAS_AUTH_HOME", str(tmp_path / "auth"))
    write_token_record(
        {
            "schema": "agentlas-oauth-v1",
            "base_url": "https://agentlas.test",
            "client_id": "client-1",
            "token_endpoint": "https://agentlas.test/api/mcp/oauth/token",
            "access_token": "expired-access",
            "refresh_token": "refresh-1",
            "expires_at": 1,
        },
        "https://agentlas.test",
    )

    def fake_urlopen(request, timeout=20):
        body = urllib.parse.parse_qs(request.data.decode("utf-8"))
        assert body["grant_type"] == ["refresh_token"]
        assert body["client_id"] == ["client-1"]
        assert body["refresh_token"] == ["refresh-1"]
        return FakeResponse(
            {
                "access_token": "new-access",
                "refresh_token": "refresh-2",
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "mcp",
            }
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    assert ensure_access_token("https://agentlas.test", interactive=False) == "new-access"
    status = auth_status("https://agentlas.test")
    assert status["status"] == "authenticated"
    stored = (tmp_path / "auth" / "agentlas.test.json").read_text(encoding="utf-8")
    assert "new-access" in stored
    assert token_path("https://agentlas.test").name == "agentlas.test.json"


def test_hub_client_auto_opens_auth_once_on_auth_required(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTLAS_AUTH_HOME", str(tmp_path / "auth"))
    ensure_calls = []

    def fake_ensure_access_token(base_url, interactive=False):
        ensure_calls.append((base_url, interactive))
        return "new-token" if interactive else None

    def fake_urlopen(request, timeout=15):
        if request.get_header("Authorization") == "Bearer new-token":
            return FakeResponse({"result": {"content": [{"type": "text", "text": '{"ok": true}'}]}})
        return FakeResponse(
            {
                "result": {
                    "isError": True,
                    "content": [{"type": "text", "text": '{"error":"auth_required"}'}],
                }
            }
        )

    monkeypatch.setattr("agentlas_cloud.networking.hub_client.ensure_access_token", fake_ensure_access_token)
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    result = call_hub_tool("agentlas.teams.invoke", {"slug": "demo"}, home=tmp_path)
    assert result == {"ok": True}
    assert ensure_calls == [("https://agentlas.cloud", False), ("https://agentlas.cloud", True)]
