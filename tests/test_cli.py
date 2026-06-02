from pathlib import Path

from typer.testing import CliRunner

from keel.cli import app


def test_cli_discover_does_not_write_by_default(tmp_path: Path) -> None:
    fixtures = Path(__file__).parent / "fixtures"
    _copy_project(tmp_path, fixtures, "sample_clean_graph.json")
    runner = CliRunner()

    result = runner.invoke(app, ["discover", str(tmp_path)])

    assert result.exit_code == 0
    assert "ui_never_touches_database" in result.stdout
    assert not (tmp_path / "keel-out" / "proposals.yml").exists()


def test_cli_check_returns_nonzero_for_regression(tmp_path: Path) -> None:
    fixtures = Path(__file__).parent / "fixtures"
    _copy_project(tmp_path, fixtures, "sample_regressed_graph.json")
    runner = CliRunner()

    result = runner.invoke(app, ["check", str(tmp_path)])

    assert result.exit_code == 1
    assert "Keel blocked 1 architecture regression" in result.stdout


def test_cli_check_json_html_and_events(tmp_path: Path) -> None:
    fixtures = Path(__file__).parent / "fixtures"
    _copy_project(tmp_path, fixtures, "sample_clean_graph.json")
    runner = CliRunner()

    result = runner.invoke(app, ["check", str(tmp_path), "--json", "--html"])
    events = runner.invoke(app, ["events", str(tmp_path)])

    assert result.exit_code == 0
    assert '"status": "passed"' in result.stdout
    assert (tmp_path / "keel-out" / "check-report.html").exists()
    assert "check" in events.stdout


def test_cli_approve_is_idempotent(tmp_path: Path) -> None:
    fixtures = Path(__file__).parent / "fixtures"
    _copy_project(tmp_path, fixtures, "sample_clean_graph.json")
    runner = CliRunner()

    discover = runner.invoke(app, ["discover", str(tmp_path), "--write"])
    first = runner.invoke(app, ["approve", "ui_never_touches_database", str(tmp_path)])
    second = runner.invoke(app, ["approve", "ui_never_touches_database", str(tmp_path)])

    assert discover.exit_code == 0
    assert first.exit_code == 0
    assert second.exit_code == 0
    assert "Approved ui_never_touches_database" in second.stdout


def test_cli_dashboard_graph_quality_and_pr_comment(tmp_path: Path) -> None:
    fixtures = Path(__file__).parent / "fixtures"
    _copy_project(tmp_path, fixtures, "sample_clean_graph.json")
    runner = CliRunner()

    quality = runner.invoke(app, ["graph-quality", str(tmp_path), "--json"])
    dashboard = runner.invoke(app, ["dashboard", str(tmp_path)])
    pr_comment = runner.invoke(app, ["pr-comment", str(tmp_path)])

    assert quality.exit_code == 0
    assert '"score"' in quality.stdout
    assert dashboard.exit_code == 0
    assert (tmp_path / "keel-out" / "dashboard.html").exists()
    assert pr_comment.exit_code == 0
    assert "pr-comment.md" in pr_comment.stdout


def test_cli_adr_compile(tmp_path: Path) -> None:
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "0001-ui-boundary.md").write_text(
        """---
keel_contract:
  id: ui_never_touches_database
  title: UI must not access DATABASE directly
  rule:
    forbid_edge:
      from_layer: UI
      to_layer: DATABASE
      relation: "*"
---
# UI Boundary
""",
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(app, ["adr-compile", str(tmp_path), "--write", "--json"])

    assert result.exit_code == 0
    assert "ui_never_touches_database" in result.stdout
    assert (tmp_path / "keel-out" / "adr-contracts.yml").exists()


def test_cli_plug_and_play_commands(tmp_path: Path) -> None:
    runner = CliRunner()

    init = runner.invoke(app, ["init", str(tmp_path), "--preset", "node"])
    doctor = runner.invoke(app, ["doctor", str(tmp_path), "--json"])
    mcp = runner.invoke(app, ["mcp-config", str(tmp_path), "--client", "codex"])
    quickstart = runner.invoke(app, ["quickstart", str(tmp_path), "--skip-graph", "--json"])

    assert init.exit_code == 0
    assert "src/components" in (tmp_path / ".keel.yml").read_text(encoding="utf-8")
    assert doctor.exit_code == 0
    assert '"keel_config"' in doctor.stdout
    assert mcp.exit_code == 0
    assert '"keel"' in mcp.stdout
    assert quickstart.exit_code == 0
    assert '"keel build ."' in quickstart.stdout


def test_cli_memory_commands(tmp_path: Path) -> None:
    runner = CliRunner()

    remember = runner.invoke(
        app,
        [
            "remember",
            "Always update buildkeelupdates.md after every build change.",
            "--repo",
            str(tmp_path),
            "--kind",
            "preference",
            "--tag",
            "agent",
        ],
    )
    recall = runner.invoke(app, ["recall", "build updates", "--repo", str(tmp_path)])
    memories = runner.invoke(app, ["memories", "--repo", str(tmp_path)])

    assert remember.exit_code == 0
    assert "Remembered memory" in remember.stdout
    assert recall.exit_code == 0
    assert "buildkeelupdates.md" in recall.stdout
    assert memories.exit_code == 0
    assert "preference" in memories.stdout


def test_cli_remember_from_project(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo\n\nKeel is a memory engine.", encoding="utf-8")
    runner = CliRunner()

    remember = runner.invoke(app, ["remember", "--from-project", "--repo", str(tmp_path), "--json"])
    recall = runner.invoke(app, ["recall", "memory engine", "--repo", str(tmp_path), "--json"])

    assert remember.exit_code == 0
    assert '"count": 1' in remember.stdout
    assert recall.exit_code == 0
    assert '"Project README Summary"' in recall.stdout


def test_cli_memory_context_eval_and_hooks(tmp_path: Path) -> None:
    runner = CliRunner()
    runner.invoke(
        app,
        [
            "remember",
            "Run tests with python -m pytest.",
            "--repo",
            str(tmp_path),
            "--kind",
            "test",
            "--gate",
        ],
    )

    context = runner.invoke(app, ["context", "how to test", "--repo", str(tmp_path)])
    evaluation = runner.invoke(app, ["eval", str(tmp_path), "--json"])
    hooks = runner.invoke(app, ["hooks", str(tmp_path), "--client", "codex", "--write"])
    architecture = runner.invoke(app, ["memory-architecture", str(tmp_path), "--write"])
    architecture_json = runner.invoke(app, ["memory-architecture", str(tmp_path), "--json"])

    assert context.exit_code == 0
    assert "Keel Memory Context" in context.stdout
    assert evaluation.exit_code == 0
    assert '"suite": "keel-memory-v1"' in evaluation.stdout
    assert (tmp_path / "keel-out" / "memory-eval.json").exists()
    assert hooks.exit_code == 0
    assert "session_start" in hooks.stdout
    assert (tmp_path / "keel-out" / "hooks" / "codex-hooks.json").exists()
    assert architecture.exit_code == 0
    assert (tmp_path / "keel-out" / "memory-architecture.md").exists()
    assert architecture_json.exit_code == 0
    assert '"principles"' in architecture_json.stdout


def test_cli_agent_setup_and_sync(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Demo\n\nKeel manages project memory.", encoding="utf-8")
    runner = CliRunner()

    sync = runner.invoke(app, ["sync", str(tmp_path), "--no-graph", "--json"])
    setup = runner.invoke(app, ["agent-setup", str(tmp_path), "--client", "claude-code", "--write", "--json"])
    manager_status = runner.invoke(app, ["manager-status", str(tmp_path), "--json"])
    graph_status = runner.invoke(app, ["graph-status", str(tmp_path), "--json"])

    assert sync.exit_code == 0
    assert '"memory_count": 1' in sync.stdout
    assert setup.exit_code == 0
    assert '"mcpServers"' in setup.stdout
    assert "mcp_project_sync" in setup.stdout
    assert "mcp_project_status" in setup.stdout
    assert (tmp_path / "keel-out" / "agent-setup" / "claude-code.json").exists()
    assert (tmp_path / "keel-out" / "agent-setup" / "claude-code-KEEL.md").exists()
    assert manager_status.exit_code == 0
    assert '"memory_count": 1' in manager_status.stdout
    assert graph_status.exit_code == 0
    assert '"exists": false' in graph_status.stdout


def _copy_project(tmp_path: Path, fixtures: Path, graph_name: str) -> None:
    (tmp_path / ".keel.yml").write_text((fixtures / "sample.keel.yml").read_text(encoding="utf-8"), encoding="utf-8")
    graph_dir = tmp_path / "graphify-out"
    graph_dir.mkdir()
    (graph_dir / "graph.json").write_text((fixtures / graph_name).read_text(encoding="utf-8"), encoding="utf-8")
