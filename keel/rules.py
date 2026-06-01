from __future__ import annotations

import networkx as nx

from .models import KeelGraph, Rule, Violation


def check_rules(graph: KeelGraph, rules: list[Rule]) -> list[Violation]:
    violations: list[Violation] = []
    for rule in rules:
        if rule.kind == "forbid":
            violations.extend(_check_forbid(graph, rule))
        elif rule.kind == "no_cycles":
            violations.extend(_check_no_cycles(graph, rule))
    return violations


def _check_forbid(graph: KeelGraph, rule: Rule) -> list[Violation]:
    violations: list[Violation] = []
    for connection in graph.connections:
        source = graph.nodes.get(connection.source)
        target = graph.nodes.get(connection.target)
        if not source or not target:
            continue
        relation_matches = rule.relation == "*" or connection.relation == rule.relation
        if source.layer == rule.from_layer and target.layer == rule.to_layer and relation_matches:
            violations.append(
                Violation(
                    contract_id=rule.describe(),
                    contract_title=rule.describe(),
                    message=(
                        f"{source.source_file} ({source.layer}) {connection.relation} "
                        f"{target.label} ({target.layer}) - forbidden by rule {rule.describe()}"
                    ),
                    source_file=source.source_file,
                    source_id=source.id,
                    target_id=target.id,
                )
            )
    return violations


def _check_no_cycles(graph: KeelGraph, rule: Rule) -> list[Violation]:
    dependency_graph = nx.DiGraph()
    for connection in graph.connections:
        source = graph.nodes.get(connection.source)
        target = graph.nodes.get(connection.target)
        if not source or not target:
            continue
        dependency_graph.add_edge(source.layer, target.layer)
    return [
        Violation(
            contract_id=rule.describe(),
            contract_title=rule.describe(),
            message="Layer cycle detected: " + " -> ".join(cycle + [cycle[0]]),
        )
        for cycle in list(nx.simple_cycles(dependency_graph))[:20]
        if len(cycle) > 1
    ]

