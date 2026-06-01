from pathlib import Path

from keel.config import load_config
from keel.graph import load_graph
from keel.layers import assign_layers_and_zones


def test_layers_and_zones_are_assigned_by_longest_prefix(tmp_path: Path) -> None:
    fixtures = Path(__file__).parent / "fixtures"
    (tmp_path / ".keel.yml").write_text((fixtures / "sample.keel.yml").read_text(encoding="utf-8"), encoding="utf-8")
    config = load_config(tmp_path)
    graph = load_graph(fixtures / "sample_clean_graph.json")

    assign_layers_and_zones(graph, config)

    assert graph.nodes["ui1"].layer == "UI"
    assert graph.nodes["svc1"].layer == "SERVICE"
    assert graph.nodes["db1"].zones == ["user"]

