import sys
from pathlib import Path

from typer.testing import CliRunner

from keel.brief import make_brief
from keel.cli import app
from keel.config import load_config
from keel.graph import load_graph
from keel.layers import assign_layers_and_zones
from keel.record import blackbox_report, get_session, list_sessions, log_action, record_note, run_command, start_session
from keel.serve import (
    blackbox_note,
    blackbox_report_text,
    blackbox_run,
    blackbox_sessions,
    blackbox_start,
    check_change,
    get_brief,
    get_replay,
    memory_bootstrap,
    memory_context,
    memory_search,
    memory_write,
    project_status,
    project_sync,
    record_action,
)


def test_brief_contains_layers_rules_and_instruction(tmp_path: Path) -> None:
    fixtures = Path(__file__).parent / "fixtures"
    _copy_guide_project(tmp_path, fixtures)
    config = load_config(tmp_path)
    graph = load_graph(tmp_path / "graphify-out" / "graph.json")
    assign_layers_and_zones(graph, config)

    brief = make_brief(graph, config)

    assert "UI" in brief
    assert "UI -> DATABASE forbidden" in brief
    assert "Route calls through the correct layer" in brief


def test_record_replay_orders_events(tmp_path: Path) -> None:
    session_id = start_session(tmp_path)
    log_action(tmp_path, session_id, "start", {"ok": True})
    log_action(tmp_path, session_id, "finish", {"ok": True})

    events = get_session(tmp_path, session_id)

    assert [event["kind"] for event in events] == ["start", "finish"]


def test_blackbox_records_command_output_and_snapshot(tmp_path: Path) -> None:
    command = f'"{sys.executable}" -c "print(123)"'
    session_id = start_session(tmp_path, label="test")

    result = run_command(tmp_path, command, session_id=session_id)
    record_note(tmp_path, "Use the blackbox as evidence.", session_id=session_id, kind="decision")
    sessions = list_sessions(tmp_path)
    report = blackbox_report(tmp_path, session_id)

    assert result["ok"] is True
    assert result["returncode"] == 0
    assert "123" in result["stdout_tail"]
    assert result["graph"]["exists"] is False
    assert sessions[0]["label"] == "test"
    assert "Use the blackbox as evidence." in report
    assert "command" in report


def test_cli_build_brief_and_replay(tmp_path: Path) -> None:
    fixtures = Path(__file__).parent / "fixtures"
    _copy_guide_project(tmp_path, fixtures)
    session_id = start_session(tmp_path)
    log_action(tmp_path, session_id, "edit", {"file": "src/components/Dashboard.tsx"})
    runner = CliRunner()

    build = runner.invoke(app, ["build", str(tmp_path)])
    brief = runner.invoke(app, ["brief", str(tmp_path)])
    replay = runner.invoke(app, ["replay", str(session_id), str(tmp_path)])

    assert build.exit_code == 0
    assert (tmp_path / "keel-out" / "keel-graph.json").exists()
    assert "Built Keel graph" in build.stdout
    assert brief.exit_code == 0
    assert "Keel Architecture Brief" in brief.stdout
    assert replay.exit_code == 0
    assert "edit" in replay.stdout


def test_cli_blackbox_commands(tmp_path: Path) -> None:
    runner = CliRunner()
    command = f'"{sys.executable}" -c "print(456)"'

    started = runner.invoke(app, ["session-start", str(tmp_path), "--label", "cli", "--json"])
    session_id = "1"
    run = runner.invoke(app, ["run", command, "--repo", str(tmp_path), "--session", session_id])
    note = runner.invoke(app, ["blackbox-note", "CLI decision", "--repo", str(tmp_path), "--session", session_id, "--kind", "decision"])
    sessions = runner.invoke(app, ["sessions", str(tmp_path)])
    report = runner.invoke(app, ["blackbox-report", session_id, str(tmp_path)])
    ended = runner.invoke(app, ["session-end", session_id, str(tmp_path), "--json"])

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


def test_cli_check_on_guide_fixtures_matches_acceptance() -> None:
    fixtures = Path(__file__).parent / "fixtures"
    runner = CliRunner()

    result = runner.invoke(app, ["check", str(fixtures)])

    assert result.exit_code == 1
    assert "forbidden by rule UI -> DATABASE forbidden" in result.stdout


def test_serve_helpers(tmp_path: Path) -> None:
    fixtures = Path(__file__).parent / "fixtures"
    _copy_guide_project(tmp_path, fixtures)

    brief = get_brief(tmp_path)
    messages = check_change(["src/components/Dashboard.tsx"], tmp_path)
    record = record_action("tool", {"name": "edit"}, repo_path=tmp_path)
    replay = get_replay(record["session_id"], tmp_path)

    assert "Keel Architecture Brief" in brief
    assert messages
    assert record["ok"] is True
    assert "tool" in replay


def test_serve_memory_helpers(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo\n\nKeel remembers project context.", encoding="utf-8")

    bootstrap = memory_bootstrap(tmp_path)
    write = memory_write("Codex should recall architecture before editing.", kind="preference", tags=["codex"], repo_path=tmp_path)
    matches = memory_search("what should codex recall?", repo_path=tmp_path)
    context = memory_context("codex architecture", repo_path=tmp_path)
    sync = project_sync(update_graph=False, repo_path=tmp_path)
    status = project_status(repo_path=tmp_path)

    assert bootstrap["count"] == 1
    assert write["ok"] is True
    assert matches[0]["kind"] == "preference"
    assert "Keel Memory Context" in context
    assert sync["memory_count"] == 1
    assert status["memory_count"] >= 1


def test_serve_blackbox_helpers(tmp_path: Path) -> None:
    session = blackbox_start(label="mcp", repo_path=tmp_path)
    command = f'"{sys.executable}" -c "print(789)"'

    run = blackbox_run(command, session_id=session["session_id"], repo_path=tmp_path)
    note = blackbox_note("MCP decision", session_id=session["session_id"], kind="decision", repo_path=tmp_path)
    sessions = blackbox_sessions(repo_path=tmp_path)
    report = blackbox_report_text(session["session_id"], repo_path=tmp_path)

    assert run["ok"] is True
    assert "789" in run["stdout_tail"]
    assert note["ok"] is True
    assert sessions[0]["label"] == "mcp"
    assert "MCP decision" in report


def _copy_guide_project(tmp_path: Path, fixtures: Path) -> None:
    (tmp_path / ".keel.yml").write_text((fixtures / "guide.keel.yml").read_text(encoding="utf-8"), encoding="utf-8")
    graph_dir = tmp_path / "graphify-out"
    graph_dir.mkdir()
    (graph_dir / "graph.json").write_text((fixtures / "sample_graph.json").read_text(encoding="utf-8"), encoding="utf-8")
