from __future__ import annotations

import json
from pathlib import Path

from .config import load_config
from .graph import load_graph
from .graphify_runner import ensure_graph
from .layers import assign_layers_and_zones


def graph_quality(repo_path: Path) -> dict:
    graph_path = ensure_graph(repo_path)
    raw = json.loads(graph_path.read_text(encoding="utf-8"))
    config = load_config(repo_path)
    graph = load_graph(graph_path)
    assign_layers_and_zones(graph, config)

    raw_nodes = raw.get("nodes", []) or []
    raw_edges = raw.get("links") or raw.get("edges") or []
    code_nodes = list(graph.nodes.values())
    unknown = [node for node in code_nodes if node.layer == "UNKNOWN"]
    inferred_edges = [edge for edge in raw_edges if edge.get("confidence") == "INFERRED"]
    ambiguous_edges = [edge for edge in raw_edges if edge.get("confidence") == "AMBIGUOUS"]

    warnings: list[str] = []
    if not raw_nodes:
        warnings.append("Graph has no nodes.")
    if code_nodes and len(unknown) / len(code_nodes) > 0.25:
        warnings.append("More than 25% of code nodes have UNKNOWN layer.")
    if raw_edges and len(ambiguous_edges) / len(raw_edges) > 0.1:
        warnings.append("More than 10% of graph edges are AMBIGUOUS.")
    if not config.layers:
        warnings.append("No layers configured in .keel.yml; discovery and checks will be limited.")

    score = 100
    if raw_nodes:
        score -= int((len(unknown) / max(len(code_nodes), 1)) * 35)
        score -= int((len(ambiguous_edges) / max(len(raw_edges), 1)) * 25)
        score -= int((len(inferred_edges) / max(len(raw_edges), 1)) * 10)
    if not config.layers:
        score -= 25
    score = max(0, min(100, score))

    return {
        "score": score,
        "status": "ok" if score >= 75 else "needs_attention",
        "graph_path": str(graph_path),
        "nodes": len(raw_nodes),
        "edges": len(raw_edges),
        "code_nodes": len(code_nodes),
        "unknown_layer_nodes": len(unknown),
        "inferred_edges": len(inferred_edges),
        "ambiguous_edges": len(ambiguous_edges),
        "warnings": warnings,
    }

