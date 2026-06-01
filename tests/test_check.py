from pathlib import Path

from keel.check import check_contract, check_repo_result, write_baseline
from keel.config import load_config
from keel.contracts import load_approved_contracts
from keel.graph import load_graph
from keel.layers import assign_layers_and_zones


def test_clean_graph_passes_after_approval(tmp_path: Path) -> None:
    config, graph = _load(tmp_path, "sample_clean_graph.json")
    contract = load_approved_contracts(config)[0]

    assert check_contract(graph, contract) == []


def test_regressed_graph_fails_with_repair_hint(tmp_path: Path) -> None:
    config, graph = _load(tmp_path, "sample_regressed_graph.json")
    contract = load_approved_contracts(config)[0]

    violations = check_contract(graph, contract)

    assert len(violations) == 1
    assert violations[0].source_file == "src/components/Dashboard.tsx"
    assert "Move this dependency through SERVICE" in violations[0].repair_hint


def test_baseline_splits_known_debt_from_blocking(tmp_path: Path) -> None:
    fixtures = Path(__file__).parent / "fixtures"
    _copy_repo_graph(tmp_path, fixtures, "sample_regressed_graph.json")

    write_baseline(tmp_path)
    result = check_repo_result(tmp_path)

    assert result.blocking == []
    assert len(result.known_debt) == 1


def _load(tmp_path: Path, graph_name: str):
    fixtures = Path(__file__).parent / "fixtures"
    (tmp_path / ".keel.yml").write_text((fixtures / "sample.keel.yml").read_text(encoding="utf-8"), encoding="utf-8")
    config = load_config(tmp_path)
    graph = load_graph(fixtures / graph_name)
    assign_layers_and_zones(graph, config)
    return config, graph


def _copy_repo_graph(tmp_path: Path, fixtures: Path, graph_name: str) -> None:
    (tmp_path / ".keel.yml").write_text((fixtures / "sample.keel.yml").read_text(encoding="utf-8"), encoding="utf-8")
    graph_dir = tmp_path / "graphify-out"
    graph_dir.mkdir()
    (graph_dir / "graph.json").write_text((fixtures / graph_name).read_text(encoding="utf-8"), encoding="utf-8")
