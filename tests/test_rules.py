from pathlib import Path

from keel.config import load_config
from keel.graph import load_graph
from keel.layers import assign_layers_and_zones
from keel.rules import check_rules


def test_guide_rules_detect_single_forbidden_edge(tmp_path: Path) -> None:
    fixtures = Path(__file__).parent / "fixtures"
    (tmp_path / ".keel.yml").write_text((fixtures / "guide.keel.yml").read_text(encoding="utf-8"), encoding="utf-8")
    graph_dir = tmp_path / "graphify-out"
    graph_dir.mkdir()
    (graph_dir / "graph.json").write_text((fixtures / "sample_graph.json").read_text(encoding="utf-8"), encoding="utf-8")
    config = load_config(tmp_path)
    graph = load_graph(graph_dir / "graph.json")
    assign_layers_and_zones(graph, config)

    violations = check_rules(graph, config.rules)

    assert len(violations) == 1
    assert "UI -> DATABASE forbidden" in violations[0].message

