from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from .models import ApprovedContract, Config, ContractRule, Evidence, Rule

VALID_RULES = {
    "forbid_edge",
    "allow_only_path",
    "external_package_scope",
    "zone_ownership",
    "no_cycles_between_layers",
}


def default_config(project_name: str = "demo-app") -> Config:
    return Config(
        version=1,
        project={"name": project_name},
        graph={"provider": "graphify", "path": "graphify-out/graph.json"},
        layers={},
        zones={},
        ignore=["node_modules", "dist", "build", "coverage", "generated"],
        approved_contracts=[],
        rules=[],
    )


def load_config(repo_path: Path) -> Config:
    path = repo_path / ".keel.yml"
    if not path.exists():
        return default_config(repo_path.name)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if raw.get("version") != 1:
        raise ValueError("Unsupported .keel.yml version; expected version: 1")

    layers = _string_list_map(raw.get("layers", {}), "layers")
    zones = _string_list_map(raw.get("zones", {}), "zones")
    contracts = [_parse_contract(item, layers, zones) for item in raw.get("approved_contracts", []) or []]
    rules = [_parse_rule(item, layers) for item in raw.get("rules", []) or []]
    ids = [contract.id for contract in contracts]
    if len(ids) != len(set(ids)):
        raise ValueError("Contract ids must be unique")

    return Config(
        version=1,
        project=dict(raw.get("project", {}) or {}),
        graph=dict(raw.get("graph", {}) or {"provider": "graphify", "path": "graphify-out/graph.json"}),
        layers=layers,
        zones=zones,
        ignore=list(raw.get("ignore", []) or []),
        approved_contracts=contracts,
        rules=rules or [rule for contract in contracts if (rule := _contract_to_rule(contract)) is not None],
    )


def save_config(repo_path: Path, config: Config) -> None:
    data: dict[str, Any] = {
        "version": config.version,
        "project": config.project,
        "graph": config.graph,
        "layers": config.layers,
        "zones": config.zones,
        "ignore": config.ignore,
        "approved_contracts": [_contract_to_yaml(contract) for contract in config.approved_contracts],
    }
    if config.rules and not config.approved_contracts:
        data["rules"] = [_rule_to_yaml(rule) for rule in config.rules]
    (repo_path / ".keel.yml").write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _string_list_map(value: Any, field_name: str) -> dict[str, list[str]]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a mapping")
    result: dict[str, list[str]] = {}
    for key, prefixes in value.items():
        if not isinstance(key, str):
            raise ValueError(f"{field_name} names must be strings")
        if not isinstance(prefixes, list) or not all(isinstance(prefix, str) for prefix in prefixes):
            raise ValueError(f"{field_name}.{key} must be a list of strings")
        result[key] = prefixes
    return result


def _parse_contract(raw: dict[str, Any], layers: dict[str, list[str]], zones: dict[str, list[str]]) -> ApprovedContract:
    rule_block = raw.get("rule") or {}
    if len(rule_block) != 1:
        raise ValueError(f"Contract {raw.get('id', '<unknown>')} must contain exactly one rule")
    kind, params = next(iter(rule_block.items()))
    if kind not in VALID_RULES:
        raise ValueError(f"Unknown contract rule: {kind}")
    _validate_rule_refs(kind, params or {}, layers, zones)
    evidence_raw = raw.get("evidence") or {}
    evidence = Evidence(
        summary=str(evidence_raw.get("summary", "")),
        facts={k: v for k, v in evidence_raw.items() if k not in {"summary", "examples"}},
        examples=list(evidence_raw.get("examples", []) or []),
    )
    return ApprovedContract(
        id=str(raw["id"]),
        title=str(raw.get("title", raw["id"])),
        source=raw.get("source", "manual"),
        status=raw.get("status", "approved"),
        rule=ContractRule(kind=kind, params=dict(params or {})),
        evidence=evidence,
        repair=dict(raw.get("repair", {}) or {}),
    )


def _validate_rule_refs(kind: str, params: dict[str, Any], layers: dict[str, list[str]], zones: dict[str, list[str]]) -> None:
    layer_refs: list[str] = []
    zone_refs: list[str] = []
    if kind == "forbid_edge":
        layer_refs.extend([params.get("from_layer"), params.get("to_layer")])
    elif kind == "allow_only_path":
        layer_refs.extend(params.get("route", []) or [])
    elif kind == "external_package_scope":
        zone_refs.extend(params.get("allowed_zones", []) or [])
        layer_refs.extend(params.get("allowed_layers", []) or [])
    elif kind == "zone_ownership":
        zone_refs.append(params.get("zone"))
        zone_refs.extend(params.get("allowed_from_zones", []) or [])
        layer_refs.extend(params.get("allowed_from_layers", []) or [])
    elif kind == "no_cycles_between_layers":
        layer_refs.extend(params.get("layers", []) or [])
    missing_layers = [layer for layer in layer_refs if layer and layer not in layers]
    missing_zones = [zone for zone in zone_refs if zone and zone not in zones]
    if missing_layers:
        raise ValueError(f"Contract references unknown layer(s): {', '.join(missing_layers)}")
    if missing_zones:
        raise ValueError(f"Contract references unknown zone(s): {', '.join(missing_zones)}")


def _contract_to_yaml(contract: ApprovedContract) -> dict[str, Any]:
    evidence = {"summary": contract.evidence.summary, **contract.evidence.facts}
    if contract.evidence.examples:
        evidence["examples"] = contract.evidence.examples
    return {
        "id": contract.id,
        "title": contract.title,
        "source": contract.source,
        "status": contract.status,
        "evidence": evidence,
        "rule": {contract.rule.kind: contract.rule.params},
        "repair": contract.repair,
    }


def proposal_to_yaml(proposal: Any) -> dict[str, Any]:
    data = asdict(proposal)
    data["rule"] = {proposal.rule.kind: proposal.rule.params}
    data["evidence"] = {"summary": proposal.evidence.summary, **proposal.evidence.facts}
    if proposal.evidence.examples:
        data["evidence"]["examples"] = proposal.evidence.examples
    return data


def _parse_rule(raw: dict[str, Any], layers: dict[str, list[str]]) -> Rule:
    if "forbid" in raw:
        params = raw.get("forbid") or {}
        from_layer = params.get("from")
        to_layer = params.get("to")
        for ref in [from_layer, to_layer]:
            if ref not in layers:
                raise ValueError(f"Rule references unknown layer: {ref}")
        return Rule(kind="forbid", from_layer=from_layer, to_layer=to_layer, relation=params.get("relation", "*"))
    if "no_cycles" in raw:
        if not isinstance(raw.get("no_cycles"), bool):
            raise ValueError("no_cycles rule must be a boolean")
        return Rule(kind="no_cycles")
    raise ValueError(f"Unknown rule shape: {raw}")


def _contract_to_rule(contract: ApprovedContract) -> Rule | None:
    if contract.status != "approved":
        return None
    if contract.rule.kind == "forbid_edge":
        return Rule(
            kind="forbid",
            from_layer=contract.rule.params.get("from_layer"),
            to_layer=contract.rule.params.get("to_layer"),
            relation=contract.rule.params.get("relation", "*"),
        )
    if contract.rule.kind == "no_cycles_between_layers":
        return Rule(kind="no_cycles")
    return None


def _rule_to_yaml(rule: Rule) -> dict[str, Any]:
    if rule.kind == "no_cycles":
        return {"no_cycles": True}
    data = {"from": rule.from_layer, "to": rule.to_layer}
    if rule.relation != "*":
        data["relation"] = rule.relation
    return {"forbid": data}
