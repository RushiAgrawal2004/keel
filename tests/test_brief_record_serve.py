from pathlib import Path

from typer.testing import CliRunner

from keel.brief import make_brief
from keel.cli import app
from keel.config import load_config
from keel.graph import load_graph
from keel.layers import assign_layers_and_zones
from keel.record import get_session, log_action, start_session
from keel.serve import (
    check_change,
    get_brief,
    get_replay,
    memory_bootstrap,
    memory_context,
    memory_search,
    memory_write,
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

    assert bootstrap["count"] == 1
    assert write["ok"] is True
    assert matches[0]["kind"] == "preference"
    assert "Keel Memory Context" in context


def _copy_guide_project(tmp_path: Path, fixtures: Path) -> None:
    (tmp_path / ".keel.yml").write_text((fixtures / "guide.keel.yml").read_text(encoding="utf-8"), encoding="utf-8")
    graph_dir = tmp_path / "graphify-out"
    graph_dir.mkdir()
    (graph_dir / "graph.json").write_text((fixtures / "sample_graph.json").read_text(encoding="utf-8"), encoding="utf-8")
