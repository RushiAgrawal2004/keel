from __future__ import annotations

from .models import ApprovedContract, KeelGraph, Violation


def repair_hint(graph: KeelGraph, contract: ApprovedContract, violation: Violation) -> str | None:
    if contract.rule.kind == "forbid_edge":
        route = contract.repair.get("route_through_layer")
        if route:
            candidates = _candidate_files(graph, route, violation.target_id)
            suffix = f" Existing candidates: {', '.join(candidates[:3])}." if candidates else ""
            return f"Move this dependency through {route}.{suffix}"
        return "Remove the direct dependency or route it through an approved boundary."
    if contract.rule.kind == "allow_only_path":
        return "Follow the approved route: " + " -> ".join(contract.rule.params.get("route", [])) + "."
    if contract.rule.kind == "external_package_scope":
        package = contract.rule.params.get("package")
        return f"Keep package {package} inside the approved scope. Add a boundary method instead of importing it here."
    if contract.rule.kind == "zone_ownership":
        return f"Access {contract.rule.params.get('zone')} through an approved API or service boundary."
    if contract.rule.kind == "no_cycles_between_layers":
        return "Break the layer cycle by moving the dependency to follow the approved layer direction."
    return None


def _candidate_files(graph: KeelGraph, layer: str, target_id: str | None) -> list[str]:
    candidates: list[str] = []
    target_zones = set(graph.nodes[target_id].zones) if target_id and target_id in graph.nodes else set()
    for node in graph.nodes.values():
        if node.layer != layer:
            continue
        if not target_zones or target_zones.intersection(node.zones):
            candidates.append(node.source_file)
    return sorted(set(candidates))

