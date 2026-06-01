from pathlib import Path

from keel.check import check_contract
from keel.config import load_config
from keel.contracts import load_approved_contracts
from keel.graph import load_graph
from keel.layers import assign_layers_and_zones


def test_repair_hint_includes_service_candidate(tmp_path: Path) -> None:
    fixtures = Path(__file__).parent / "fixtures"
    (tmp_path / ".keel.yml").write_text((fixtures / "sample.keel.yml").read_text(encoding="utf-8"), encoding="utf-8")
    config = load_config(tmp_path)
    graph = load_graph(fixtures / "sample_regressed_graph.json")
    assign_layers_and_zones(graph, config)

    violations = check_contract(graph, load_approved_contracts(config)[0])

    assert "src/services/userService.ts" in violations[0].repair_hint

