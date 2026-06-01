from pathlib import Path

from keel.graph import load_graph


def test_graph_loads_code_nodes_and_ignores_semantic_similarity() -> None:
    fixture = Path(__file__).parent / "fixtures" / "sample_graph.json"

    graph = load_graph(fixture)

    assert sorted(graph.nodes) == ["db1", "ui1"]
    assert len(graph.connections) == 1
    assert graph.connections[0].relation == "imports"

