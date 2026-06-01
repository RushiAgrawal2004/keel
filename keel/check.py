from __future__ import annotations

import hashlib
from pathlib import Path

import networkx as nx
import yaml

from .config import load_config
from .contracts import load_approved_contracts
from .graph import load_graph
from .graphify_runner import ensure_graph
from .layers import assign_layers_and_zones
from .models import ApprovedContract, CheckResult, KeelGraph, Violation
from .repair import repair_hint
from .rules import check_rules


def check_repo(repo_path: Path, changed_files: list[str] | None = None) -> list[Violation]:
    return check_repo_result(repo_path, changed_files).blocking


def check_repo_result(repo_path: Path, changed_files: list[str] | None = None) -> CheckResult:
    config = load_config(repo_path)
    graph_path = ensure_graph(repo_path)
    graph = load_graph(graph_path)
    assign_layers_and_zones(graph, config)
    violations: list[Violation] = []
    approved_contracts = load_approved_contracts(config)
    for contract in approved_contracts:
        violations.extend(check_contract(graph, contract))
    if not approved_contracts and config.rules:
        violations.extend(check_rules(graph, config.rules))
    if changed_files:
        normalized = {_normalize(path) for path in changed_files}
        violations = [
            violation
            for violation in violations
            if violation.source_file and _normalize(violation.source_file) in normalized
        ]
    return _split_baseline(repo_path, violations)


def check_contract(graph: KeelGraph, contract: ApprovedContract) -> list[Violation]:
    kind = contract.rule.kind
    if kind == "forbid_edge":
        violations = _check_forbid_edge(graph, contract)
    elif kind == "allow_only_path":
        violations = _check_allow_only_path(graph, contract)
    elif kind == "external_package_scope":
        violations = _check_external_package_scope(graph, contract)
    elif kind == "zone_ownership":
        violations = _check_zone_ownership(graph, contract)
    elif kind == "no_cycles_between_layers":
        violations = _check_no_cycles_between_layers(graph, contract)
    else:
        violations = []
    for violation in violations:
        violation.repair_hint = repair_hint(graph, contract, violation)
    return violations


def write_baseline(repo_path: Path) -> Path:
    config = load_config(repo_path)
    graph = load_graph(ensure_graph(repo_path))
    assign_layers_and_zones(graph, config)
    violations: list[Violation] = []
    for contract in load_approved_contracts(config):
        violations.extend(check_contract(graph, contract))
    out_dir = repo_path / "keel-out"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / "baseline.yml"
    path.write_text(yaml.safe_dump([_violation_key(v) for v in violations], sort_keys=False), encoding="utf-8")
    return path


def _check_forbid_edge(graph: KeelGraph, contract: ApprovedContract) -> list[Violation]:
    params = contract.rule.params
    from_layer = params.get("from_layer")
    to_layer = params.get("to_layer")
    relation = params.get("relation", "*")
    violations: list[Violation] = []
    for connection in graph.connections:
        source = graph.nodes[connection.source]
        target = graph.nodes[connection.target]
        if source.layer == from_layer and target.layer == to_layer and (relation == "*" or connection.relation == relation):
            violations.append(
                Violation(
                    contract_id=contract.id,
                    contract_title=contract.title,
                    message=f"{source.source_file} {connection.relation} {target.source_file}, violating {contract.id}.",
                    source_file=source.source_file,
                    source_id=source.id,
                    target_id=target.id,
                )
            )
    return violations


def _check_allow_only_path(graph: KeelGraph, contract: ApprovedContract) -> list[Violation]:
    route = contract.rule.params.get("route", [])
    if len(route) < 3:
        return []
    source_layer, target_layer = route[0], route[-1]
    violations: list[Violation] = []
    for connection in graph.connections:
        source = graph.nodes[connection.source]
        target = graph.nodes[connection.target]
        if source.layer == source_layer and target.layer == target_layer:
            violations.append(
                Violation(
                    contract_id=contract.id,
                    contract_title=contract.title,
                    message=f"{source.source_file} directly reaches {target.source_file} outside approved route.",
                    source_file=source.source_file,
                    source_id=source.id,
                    target_id=target.id,
                )
            )
    return violations


def _check_external_package_scope(graph: KeelGraph, contract: ApprovedContract) -> list[Violation]:
    params = contract.rule.params
    package = params.get("package")
    allowed_zones = set(params.get("allowed_zones", []) or [])
    allowed_layers = set(params.get("allowed_layers", []) or [])
    violations: list[Violation] = []
    for item in graph.external_imports:
        if item.package != package:
            continue
        node = graph.nodes[item.source_id]
        zone_ok = bool(allowed_zones and allowed_zones.intersection(node.zones))
        layer_ok = bool(allowed_layers and node.layer in allowed_layers)
        if not zone_ok and not layer_ok:
            violations.append(
                Violation(
                    contract_id=contract.id,
                    contract_title=contract.title,
                    message=f"{node.source_file} imports {package} outside its approved scope.",
                    source_file=node.source_file,
                    source_id=node.id,
                )
            )
    return violations


def _check_zone_ownership(graph: KeelGraph, contract: ApprovedContract) -> list[Violation]:
    params = contract.rule.params
    zone = params.get("zone")
    allowed_zones = set(params.get("allowed_from_zones", []) or [])
    allowed_layers = set(params.get("allowed_from_layers", []) or [])
    target_nodes = {node.id for node in graph.nodes.values() if zone in node.zones}
    violations: list[Violation] = []
    for connection in graph.connections:
        if connection.target not in target_nodes or connection.source in target_nodes:
            continue
        source = graph.nodes[connection.source]
        target = graph.nodes[connection.target]
        zone_ok = allowed_zones.intersection(source.zones)
        layer_ok = source.layer in allowed_layers
        if not zone_ok and not layer_ok:
            violations.append(
                Violation(
                    contract_id=contract.id,
                    contract_title=contract.title,
                    message=f"{source.source_file} accesses {target.source_file} outside {zone} ownership rules.",
                    source_file=source.source_file,
                    source_id=source.id,
                    target_id=target.id,
                )
            )
    return violations


def _check_no_cycles_between_layers(graph: KeelGraph, contract: ApprovedContract) -> list[Violation]:
    layers = set(contract.rule.params.get("layers", []) or [])
    layer_graph = nx.DiGraph()
    layer_graph.add_nodes_from(layers)
    for connection in graph.connections:
        source = graph.nodes[connection.source].layer
        target = graph.nodes[connection.target].layer
        if source in layers and target in layers and source != target:
            layer_graph.add_edge(source, target)
    cycles = list(nx.simple_cycles(layer_graph))
    return [
        Violation(
            contract_id=contract.id,
            contract_title=contract.title,
            message="Layer cycle detected: " + " -> ".join(cycle + [cycle[0]]),
        )
        for cycle in cycles
    ]


def _split_baseline(repo_path: Path, violations: list[Violation]) -> CheckResult:
    path = repo_path / "keel-out" / "baseline.yml"
    if not path.exists():
        return CheckResult(blocking=violations, known_debt=[])
    known = set(yaml.safe_load(path.read_text(encoding="utf-8")) or [])
    blocking: list[Violation] = []
    debt: list[Violation] = []
    for violation in violations:
        if _violation_key(violation) in known:
            debt.append(violation)
        else:
            blocking.append(violation)
    return CheckResult(blocking=blocking, known_debt=debt)


def _violation_key(violation: Violation) -> str:
    payload = "|".join(
        [
            violation.contract_id,
            violation.source_id or "",
            violation.target_id or "",
            violation.message,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize(path: str) -> str:
    return path.replace("\\", "/").strip("/")
