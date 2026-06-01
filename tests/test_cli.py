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


def _copy_project(tmp_path: Path, fixtures: Path, graph_name: str) -> None:
    (tmp_path / ".keel.yml").write_text((fixtures / "sample.keel.yml").read_text(encoding="utf-8"), encoding="utf-8")
    graph_dir = tmp_path / "graphify-out"
    graph_dir.mkdir()
    (graph_dir / "graph.json").write_text((fixtures / graph_name).read_text(encoding="utf-8"), encoding="utf-8")
