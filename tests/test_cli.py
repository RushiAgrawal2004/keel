from pathlib import Path
import subprocess
import sys

from typer.testing import CliRunner

from keel.cli import app
from keel.graphify_runner import GRAPHIFY_API_KEYS, ensure_graph


def test_disabled_commands_are_not_public(tmp_path: Path) -> None:
    runner = CliRunner()

    for command in ["discover", "check", "remember", "context", "dashboard", "pr-comment", "eval"]:
        result = runner.invoke(app, [command, str(tmp_path)])
        assert result.exit_code != 0


def test_cli_blackbox_flow(tmp_path: Path) -> None:
    runner = CliRunner()
    command = f'"{sys.executable}" -c "print(456)"'

    started = runner.invoke(app, ["session-start", str(tmp_path), "--label", "cli", "--json"])
    run = runner.invoke(app, ["run", command, "--repo", str(tmp_path), "--session", "1"])
    note = runner.invoke(app, ["blackbox-note", "CLI decision", "--repo", str(tmp_path), "--session", "1", "--kind", "decision"])
    sessions = runner.invoke(app, ["sessions", str(tmp_path)])
    report = runner.invoke(app, ["blackbox-report", "1", str(tmp_path)])
    ended = runner.invoke(app, ["session-end", "1", str(tmp_path), "--json"])

    assert started.exit_code == 0
    assert '"session_id": 1' in started.stdout
    assert run.exit_code == 0
    assert "456" in run.stdout
    assert note.exit_code == 0
    assert sessions.exit_code == 0
    assert "cli" in sessions.stdout
    assert report.exit_code == 0
    assert "CLI decision" in report.stdout
    assert ended.exit_code == 0
    assert '"status": "completed"' in ended.stdout


def test_cli_graph_status_without_graph(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["graph-status", str(tmp_path), "--json"])

    assert result.exit_code == 0
    assert '"exists": false' in result.stdout


def test_cli_mcp_and_agent_setup_are_graph_blackbox_only(tmp_path: Path) -> None:
    runner = CliRunner()

    mcp = runner.invoke(app, ["mcp-config", str(tmp_path), "--client", "codex"])
    setup = runner.invoke(app, ["agent-setup", str(tmp_path), "--client", "claude-code", "--json"])

    assert mcp.exit_code == 0
    assert '"keel"' in mcp.stdout
    assert setup.exit_code == 0
    assert "mcp_graph_build" in setup.stdout
    assert "mcp_blackbox_run" in setup.stdout
    assert "mcp_memory_search" not in setup.stdout
    assert "mcp_check_change" not in setup.stdout


def test_cli_graphify_api_key_failure_creates_env_template(tmp_path: Path, monkeypatch) -> None:
    for key in GRAPHIFY_API_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr("keel.graphify_runner.shutil.which", lambda name: "graphify")

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr="error: no LLM API key found. Set GEMINI_API_KEY or GOOGLE_API_KEY, or pass --backend.\n",
        )

    monkeypatch.setattr("keel.graphify_runner.subprocess.run", fake_run)
    runner = CliRunner()

    result = runner.invoke(app, ["graph", str(tmp_path)])
    output = result.stdout + result.stderr

    assert result.exit_code == 2
    assert "Graphify not ready" in output
    assert (tmp_path / ".env").exists()
    assert "GEMINI_API_KEY=paste_your_gemini_key_here" in (tmp_path / ".env").read_text(encoding="utf-8")
    assert ".env" in (tmp_path / ".gitignore").read_text(encoding="utf-8")


def test_graphify_loads_project_env_for_retry(tmp_path: Path, monkeypatch) -> None:
    for key in GRAPHIFY_API_KEYS:
        monkeypatch.delenv(key, raising=False)
    (tmp_path / ".env").write_text("GEMINI_API_KEY=real-test-key\n", encoding="utf-8")
    monkeypatch.setattr("keel.graphify_runner.shutil.which", lambda name: "graphify")
    calls = []

    def fake_run(*args, **kwargs):
        calls.append(kwargs["env"].get("GEMINI_API_KEY"))
        if kwargs["env"].get("GEMINI_API_KEY") == "real-test-key":
            graph_dir = tmp_path / "graphify-out"
            graph_dir.mkdir(exist_ok=True)
            (graph_dir / "graph.json").write_text('{"nodes": [], "edges": []}', encoding="utf-8")
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="ok", stderr="")
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="error: no LLM API key found")

    monkeypatch.setattr("keel.graphify_runner.subprocess.run", fake_run)

    graph_path = ensure_graph(tmp_path)

    assert graph_path == tmp_path / "graphify-out" / "graph.json"
    assert calls == ["real-test-key"]
