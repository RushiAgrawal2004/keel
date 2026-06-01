from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class Node:
    id: str
    label: str
    source_file: str
    file_type: str
    layer: str = "UNKNOWN"
    zones: list[str] = field(default_factory=list)


@dataclass
class Connection:
    source: str
    target: str
    relation: str
    confidence: str = "EXTRACTED"


@dataclass
class ExternalImport:
    source_id: str
    source_file: str
    package: str
    relation: str = "imports"


@dataclass
class KeelGraph:
    nodes: dict[str, Node] = field(default_factory=dict)
    connections: list[Connection] = field(default_factory=list)
    external_imports: list[ExternalImport] = field(default_factory=list)


@dataclass(frozen=True)
class ContractRule:
    kind: Literal[
        "forbid_edge",
        "allow_only_path",
        "external_package_scope",
        "zone_ownership",
        "no_cycles_between_layers",
    ]
    params: dict[str, Any]


@dataclass
class Evidence:
    summary: str
    facts: dict[str, Any] = field(default_factory=dict)
    examples: list[str] = field(default_factory=list)


@dataclass
class ProposedContract:
    id: str
    title: str
    confidence: Literal["low", "medium", "high"]
    rule: ContractRule
    evidence: Evidence
    repair: dict[str, Any] = field(default_factory=dict)


@dataclass
class ApprovedContract:
    id: str
    title: str
    source: Literal["discovered", "manual", "adr"]
    status: Literal["approved", "disabled"]
    rule: ContractRule
    evidence: Evidence
    repair: dict[str, Any] = field(default_factory=dict)


@dataclass
class Violation:
    contract_id: str
    contract_title: str
    message: str
    source_file: str | None = None
    source_id: str | None = None
    target_id: str | None = None
    repair_hint: str | None = None


@dataclass
class CheckResult:
    blocking: list[Violation] = field(default_factory=list)
    known_debt: list[Violation] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.blocking


@dataclass
class Config:
    version: int
    project: dict[str, Any]
    graph: dict[str, Any]
    layers: dict[str, list[str]]
    zones: dict[str, list[str]]
    ignore: list[str]
    approved_contracts: list[ApprovedContract] = field(default_factory=list)
