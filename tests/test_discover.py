from pathlib import Path

from keel.config import load_config
from keel.discover import discover_contracts
from keel.graph import load_graph
from keel.layers import assign_layers_and_zones


def test_discover_proposes_ui_never_touches_database(tmp_path: Path) -> None:
    fixtures = Path(__file__).parent / "fixtures"
    (tmp_path / ".keel.yml").write_text((fixtures / "sample.keel.yml").read_text(encoding="utf-8"), encoding="utf-8")
    config = load_config(tmp_path)
    graph = load_graph(fixtures / "sample_clean_graph.json")
    assign_layers_and_zones(graph, config)

    proposals = discover_contracts(graph, config)

    proposal_ids = {proposal.id for proposal in proposals}
    assert "ui_never_touches_database" in proposal_ids
    proposal = next(item for item in proposals if item.id == "ui_never_touches_database")
    assert proposal.confidence == "medium"
    assert proposal.evidence.facts["direct_edges_found"] == 0

