from __future__ import annotations

from collections import Counter, defaultdict
from itertools import permutations

import networkx as nx

from .models import Config, ContractRule, Evidence, KeelGraph, ProposedContract


def discover_contracts(graph: KeelGraph, config: Config, include_low: bool = False) -> list[ProposedContract]:
    proposals: list[ProposedContract] = []
    layer_counts = Counter(node.layer for node in graph.nodes.values())
    direct_counts = _direct_layer_counts(graph)

    for from_layer, to_layer in permutations(sorted(config.layers), 2):
        if from_layer == "TEST" or to_layer == "TEST":
            continue
        from_nodes = layer_counts[from_layer]
        to_nodes = layer_counts[to_layer]
        direct_edges = direct_counts[(from_layer, to_layer)]
        if from_nodes >= 5 and to_nodes >= 3 and direct_edges == 0:
            confidence = _confidence(from_nodes, to_nodes, direct_edges)
            if confidence != "low" or include_low:
                proposals.append(_forbid_edge_proposal(from_layer, to_layer, from_nodes, to_nodes, direct_edges, confidence))

    proposals.extend(_route_proposals(graph, config, direct_counts, include_low))
    proposals.extend(_package_scope_proposals(graph, include_low))
    proposals.extend(_zone_ownership_proposals(graph, config, include_low))
    dag = _dag_proposal(graph, config, include_low)
    if dag:
        proposals.append(dag)
    return _dedupe(proposals)


def _direct_layer_counts(graph: KeelGraph) -> Counter[tuple[str, str]]:
    counts: Counter[tuple[str, str]] = Counter()
    for connection in graph.connections:
        source = graph.nodes[connection.source]
        target = graph.nodes[connection.target]
        counts[(source.layer, target.layer)] += 1
    return counts


def _forbid_edge_proposal(
    from_layer: str,
    to_layer: str,
    from_nodes: int,
    to_nodes: int,
    direct_edges: int,
    confidence: str,
) -> ProposedContract:
    contract_id = f"{from_layer.lower()}_never_touches_{to_layer.lower()}"
    return ProposedContract(
        id=contract_id,
        title=f"{from_layer} must not access {to_layer} directly",
        confidence=confidence,  # type: ignore[arg-type]
        rule=ContractRule(
            kind="forbid_edge",
            params={"from_layer": from_layer, "to_layer": to_layer, "relation": "*"},
        ),
        evidence=Evidence(
            summary=f"{from_layer} has {from_nodes} nodes and {to_layer} has {to_nodes}; direct edges found: {direct_edges}.",
            facts={"from_layer_nodes": from_nodes, "to_layer_nodes": to_nodes, "direct_edges_found": direct_edges},
        ),
        repair={"route_through_layer": "SERVICE"} if "SERVICE" not in {from_layer, to_layer} else {},
    )


def _route_proposals(
    graph: KeelGraph,
    config: Config,
    direct_counts: Counter[tuple[str, str]],
    include_low: bool,
) -> list[ProposedContract]:
    proposals: list[ProposedContract] = []
    layer_graph = nx.DiGraph()
    layer_graph.add_nodes_from(config.layers)
    for connection in graph.connections:
        source_layer = graph.nodes[connection.source].layer
        target_layer = graph.nodes[connection.target].layer
        if source_layer != "UNKNOWN" and target_layer != "UNKNOWN" and source_layer != target_layer:
            layer_graph.add_edge(source_layer, target_layer)

    for a, b, c in permutations(sorted(config.layers), 3):
        if "TEST" in {a, b, c}:
            continue
        if direct_counts[(a, c)] != 0:
            continue
        if layer_graph.has_edge(a, b) and layer_graph.has_edge(b, c):
            path_count = _count_node_paths(graph, a, b, c)
            if path_count >= 3:
                confidence = "medium" if path_count < 8 else "high"
                if confidence != "low" or include_low:
                    proposals.append(
                        ProposedContract(
                            id=f"{a.lower()}_reaches_{c.lower()}_through_{b.lower()}",
                            title=f"{a} must reach {c} through {b}",
                            confidence=confidence,
                            rule=ContractRule(kind="allow_only_path", params={"route": [a, b, c]}),
                            evidence=Evidence(
                                summary=f"Observed {path_count} {a} -> {b} -> {c} paths and zero direct {a} -> {c} edges.",
                                facts={"path_count": path_count, "direct_edges_found": 0},
                            ),
                            repair={},
                        )
                    )
    return proposals


def _count_node_paths(graph: KeelGraph, a: str, b: str, c: str) -> int:
    by_source = defaultdict(list)
    for connection in graph.connections:
        by_source[connection.source].append(connection.target)
    count = 0
    for first in graph.nodes.values():
        if first.layer != a:
            continue
        for mid_id in by_source[first.id]:
            mid = graph.nodes[mid_id]
            if mid.layer != b:
                continue
            count += sum(1 for last_id in by_source[mid.id] if graph.nodes[last_id].layer == c)
    return count


def _package_scope_proposals(graph: KeelGraph, include_low: bool) -> list[ProposedContract]:
    by_package: dict[str, list[str]] = defaultdict(list)
    for item in graph.external_imports:
        node = graph.nodes.get(item.source_id)
        if node:
            by_package[item.package].extend(node.zones or [node.layer])
    proposals: list[ProposedContract] = []
    for package, owners in by_package.items():
        if len(owners) < 3:
            continue
        owner_set = sorted(set(owners))
        if len(owner_set) == 1:
            owner = owner_set[0]
            zone_param = {"allowed_zones": [owner]} if owner != "UNKNOWN" else {}
            if zone_param or include_low:
                proposals.append(
                    ProposedContract(
                        id=f"{package.replace('-', '_')}_only_from_{owner.lower()}",
                        title=f"{package} package must stay inside {owner}",
                        confidence="medium",
                        rule=ContractRule(
                            kind="external_package_scope",
                            params={"package": package, **zone_param},
                        ),
                        evidence=Evidence(
                            summary=f"{package} is imported {len(owners)} times, all from {owner}.",
                            facts={"package": package, "import_count": len(owners), "owner": owner},
                        ),
                    )
                )
    return proposals


def _zone_ownership_proposals(graph: KeelGraph, config: Config, include_low: bool) -> list[ProposedContract]:
    proposals: list[ProposedContract] = []
    for zone in sorted(config.zones):
        zone_nodes = {node.id for node in graph.nodes.values() if zone in node.zones}
        if len(zone_nodes) < 5:
            continue
        incoming_zones: set[str] = set()
        incoming_layers: set[str] = set()
        for connection in graph.connections:
            if connection.target not in zone_nodes or connection.source in zone_nodes:
                continue
            source = graph.nodes[connection.source]
            incoming_zones.update(source.zones)
            incoming_layers.add(source.layer)
        confidence = "medium" if len(zone_nodes) < 10 else "high"
        if confidence != "low" or include_low:
            proposals.append(
                ProposedContract(
                    id=f"{zone}_zone_ownership",
                    title=f"{zone} zone should have explicit ownership",
                    confidence=confidence,
                    rule=ContractRule(
                        kind="zone_ownership",
                        params={
                            "zone": zone,
                            "allowed_from_zones": sorted(incoming_zones | {zone}),
                            "allowed_from_layers": sorted(layer for layer in incoming_layers if layer != "UNKNOWN"),
                        },
                    ),
                    evidence=Evidence(
                        summary=f"{zone} has {len(zone_nodes)} nodes; incoming edges come from a limited set of owners.",
                        facts={"zone_nodes": len(zone_nodes)},
                    ),
                )
            )
    return proposals


def _dag_proposal(graph: KeelGraph, config: Config, include_low: bool) -> ProposedContract | None:
    layer_graph = nx.DiGraph()
    for layer in config.layers:
        if layer not in {"UNKNOWN", "TEST"}:
            layer_graph.add_node(layer)
    for connection in graph.connections:
        source = graph.nodes[connection.source].layer
        target = graph.nodes[connection.target].layer
        if source in layer_graph and target in layer_graph and source != target:
            layer_graph.add_edge(source, target)
    if len(layer_graph.nodes) < 3 or not nx.is_directed_acyclic_graph(layer_graph):
        return None
    confidence = "medium" if len(layer_graph.edges) < 4 else "high"
    if confidence == "low" and not include_low:
        return None
    return ProposedContract(
        id="layers_must_remain_acyclic",
        title="Configured layers must remain acyclic",
        confidence=confidence,
        rule=ContractRule(kind="no_cycles_between_layers", params={"layers": list(layer_graph.nodes)}),
        evidence=Evidence(
            summary=f"Observed layer dependency graph has {len(layer_graph.nodes)} layers and no cycles.",
            facts={"layers": list(layer_graph.nodes), "edges": list(layer_graph.edges)},
        ),
    )


def _confidence(from_nodes: int, to_nodes: int, direct_edges: int) -> str:
    if from_nodes >= 10 and to_nodes >= 5 and direct_edges == 0:
        return "high"
    if from_nodes >= 5 and to_nodes >= 3 and direct_edges == 0:
        return "medium"
    return "low"


def _dedupe(proposals: list[ProposedContract]) -> list[ProposedContract]:
    seen: set[str] = set()
    result: list[ProposedContract] = []
    for proposal in proposals:
        if proposal.id not in seen:
            seen.add(proposal.id)
            result.append(proposal)
    return result
