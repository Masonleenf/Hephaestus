import base64
import hashlib
import json

import pytest

from agentlas_cloud.networking import init_networking, save_card
from agentlas_cloud.networking.gui_shortcut import _materialize_cloud_package, open_local_gui_shortcut
from test_network_cards import make_ready_card


def _cloud_file(path: str, content: str) -> dict[str, object]:
    raw = content.encode("utf-8")
    return {
        "path": path,
        "contentBase64": base64.b64encode(raw).decode("ascii"),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def test_operator_local_gui_shortcut_requires_allow_local(tmp_path):
    home = tmp_path / "networking"
    init_networking(home)
    package = tmp_path / "startup-package"
    (package / "scripts").mkdir(parents=True)
    launcher = package / "scripts" / "open.py"
    launcher.write_text(
        "import json\n"
        "print(json.dumps({'status': 'gui_ready', 'opened': False, 'gui_url': 'file:///tmp/demo.html'}))\n",
        encoding="utf-8",
    )
    card = make_ready_card(
        tmp_path,
        "startup-gui",
        triggers_ko=["스타트업 열어줘", "창업 gui"],
        triggers_en=["startup", "startup founder studio", "open startup gui"],
        antis=["legal", "payment", "deploy"],
        capabilities=["open_startup_gui"],
    )
    card["entrypoints"] = {
        "canonical_command": "/startup",
        "agent": "agents/00-startup-orchestrator/agent.md",
        "gui": "webapp/index.html",
        "gui_launcher": "scripts/open.py",
    }
    card["network_shortcut"] = {
        "enabled": True,
        "phrases": ["local startup"],
        "mode": "local_gui",
    }
    card["source"] = {"kind": "local_path", "ref": str(package)}
    save_card(home, card)

    blocked = open_local_gui_shortcut("local startup", home=home, no_open=True)
    assert blocked["action"] == "no_local_gui_shortcut"
    assert blocked["local_routing"] == "disabled_by_default"

    result = open_local_gui_shortcut("local startup", home=home, no_open=True, allow_local=True)

    assert result["action"] == "open_gui"
    assert result["status"] == "opened"
    assert result["selected"]["id"] == "local/startup-gui"
    assert result["launcher_result"]["status"] == "gui_ready"


def test_local_gui_shortcut_requires_exact_opt_in_phrase(tmp_path):
    home = tmp_path / "networking"
    init_networking(home)
    card = make_ready_card(
        tmp_path,
        "startup-gui",
        triggers_ko=["스타트업 열어줘", "창업 gui"],
        triggers_en=["startup", "startup founder studio", "open startup gui"],
        antis=["legal", "payment", "deploy"],
        capabilities=["open_startup_gui"],
    )
    card["network_shortcut"] = {
        "enabled": True,
        "phrases": ["startup"],
        "mode": "local_gui",
    }
    save_card(home, card)

    result = open_local_gui_shortcut("startup market research", home=home, no_open=True)

    assert result == {
        "action": "no_local_gui_shortcut",
        "status": "not_found",
        "query": "startup market research",
        "quarantined": 0,
        "local_routing": "disabled_by_default",
        "hub_routing": "no_registered_gui_shortcut",
    }


def test_hub_gui_shortcut_preempts_local_paid_card(tmp_path, monkeypatch):
    home = tmp_path / "networking"
    init_networking(home)
    package = tmp_path / "paid-startup-package"
    package.mkdir()
    card = make_ready_card(
        tmp_path,
        "paid-startup-gui",
        triggers_ko=["스타트업"],
        triggers_en=["startup"],
        antis=["legal", "payment", "deploy"],
        capabilities=["open_startup_gui"],
    )
    card["entrypoints"] = {
        "canonical_command": "/startup",
        "agent": "agents/00-startup-orchestrator/agent.md",
        "gui_launcher": "scripts/local-open.py",
    }
    card["network_shortcut"] = {
        "enabled": True,
        "phrases": ["startup"],
        "mode": "local_gui",
    }
    card["source"] = {"kind": "local_path", "ref": str(package)}
    save_card(home, card)

    def fake_call(name, arguments=None, home=None, timeout=60):
        assert name == "marketplace.get_manifest"
        assert arguments == {"kind": "agent", "slug": "agentlas-startup-founder-studio"}
        files = [
            _cloud_file("agentlas.json", json.dumps({"ui": {"launcher": "scripts/open.py"}})),
            _cloud_file("scripts/open.py", "print('hub')\n"),
        ]
        return {
            "name": "Startup Founder Studio",
            "cloudPackage": {
                "packageHash": _cloud_package_hash(files),
                "files": files,
            },
        }

    monkeypatch.setattr("agentlas_cloud.networking.gui_shortcut.call_hub_tool", fake_call)
    monkeypatch.setattr(
        "agentlas_cloud.networking.gui_shortcut._launch_python_gui",
        lambda launcher, cwd, no_open, detach: {
            "status": "opened",
            "launcher_result": {"status": "hub_ready"},
            "stderr": "",
            "returncode": 0,
        },
    )
    monkeypatch.setenv("AGENTLAS_CLOUD_INSTALL_HOME", str(tmp_path / "cloud-installs"))

    result = open_local_gui_shortcut("startup", home=home, no_open=True)

    assert result["action"] == "open_gui"
    assert result["source"] == "hub_cloud_package"
    assert result["local_routing"] == "skipped"
    assert result["hub_routing"] == "cloud_package_installed"
    assert "selected" not in result


def test_cloud_package_restore_is_exact_and_preserves_last_valid_asset_on_failure(tmp_path):
    root = tmp_path / "cloud-installs" / "portable-agent"
    root.mkdir(parents=True)
    (root / "AGENTS.md").write_text("old agent\n", encoding="utf-8")
    (root / "removed-in-v2.md").write_text("stale\n", encoding="utf-8")
    (root / ".agentlas-cloud-package.json").write_text(
        json.dumps({"packageHash": "sha256:v1"}),
        encoding="utf-8",
    )
    v2_files = [
        _cloud_file("AGENTS.md", "new agent\n"),
        _cloud_file("skills/core/SKILL.md", "portable skill\n"),
    ]
    v2_hash = _cloud_package_hash(v2_files)

    _materialize_cloud_package(root, v2_files, package_hash=v2_hash)

    assert (root / "AGENTS.md").read_text(encoding="utf-8") == "new agent\n"
    assert not (root / "removed-in-v2.md").exists()

    (root / "AGENTS.md").write_text("locally mutated\n", encoding="utf-8")
    _materialize_cloud_package(root, v2_files, package_hash=v2_hash)
    assert (root / "AGENTS.md").read_text(encoding="utf-8") == "new agent\n"

    broken = _cloud_file("AGENTS.md", "broken update\n")
    broken["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="integrity failed"):
        _materialize_cloud_package(root, [broken], package_hash="0" * 64)

    assert (root / "AGENTS.md").read_text(encoding="utf-8") == "new agent\n"
    marker = json.loads((root / ".agentlas-cloud-package.json").read_text(encoding="utf-8"))
    assert marker["packageHash"] == v2_hash

    aggregate_mismatch = [_cloud_file("AGENTS.md", "aggregate mismatch\n")]
    with pytest.raises(ValueError, match="aggregate integrity failed"):
        _materialize_cloud_package(root, aggregate_mismatch, package_hash="f" * 64)
    assert (root / "AGENTS.md").read_text(encoding="utf-8") == "new agent\n"

    duplicate = [_cloud_file("AGENTS.md", "first\n"), _cloud_file("./AGENTS.md", "second\n")]
    with pytest.raises(ValueError, match="duplicate cloud package path"):
        _materialize_cloud_package(root, duplicate, package_hash=_cloud_package_hash(duplicate))
    assert (root / "AGENTS.md").read_text(encoding="utf-8") == "new agent\n"


def _cloud_package_hash(files):
    aggregate = hashlib.sha256()
    for item in sorted(files, key=lambda file: file["path"]):
        aggregate.update(item["path"].encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(item["sha256"].encode("ascii"))
        aggregate.update(b"\0")
    return aggregate.hexdigest()
