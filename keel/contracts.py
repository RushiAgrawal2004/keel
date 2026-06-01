from __future__ import annotations

from pathlib import Path

import yaml

from .config import load_config, proposal_to_yaml, save_config
from .models import ApprovedContract, ContractRule, Evidence


def load_approved_contracts(config) -> list[ApprovedContract]:
    return [contract for contract in config.approved_contracts if contract.status == "approved"]


def approve_contract(repo_path: Path, contract_id: str) -> ApprovedContract:
    config = load_config(repo_path)
    proposal_path = repo_path / "keel-out" / "proposals.yml"
    if not proposal_path.exists():
        raise FileNotFoundError("No proposals found. Run `keel discover . --write` first.")
    proposals = yaml.safe_load(proposal_path.read_text(encoding="utf-8")) or []
    raw = next((item for item in proposals if item.get("id") == contract_id), None)
    if raw is None:
        raise ValueError(f"Proposal not found: {contract_id}")
    existing = next((contract for contract in config.approved_contracts if contract.id == contract_id), None)
    if existing:
        return existing
    rule_kind, rule_params = next(iter((raw.get("rule") or {}).items()))
    evidence_raw = raw.get("evidence") or {}
    approved = ApprovedContract(
        id=raw["id"],
        title=raw.get("title", raw["id"]),
        source="discovered",
        status="approved",
        rule=ContractRule(kind=rule_kind, params=dict(rule_params or {})),
        evidence=Evidence(
            summary=str(evidence_raw.get("summary", "")),
            facts={k: v for k, v in evidence_raw.items() if k not in {"summary", "examples"}},
            examples=list(evidence_raw.get("examples", []) or []),
        ),
        repair=dict(raw.get("repair", {}) or {}),
    )
    config.approved_contracts.append(approved)
    save_config(repo_path, config)
    return approved


def reject_contract(repo_path: Path, contract_id: str) -> None:
    out_dir = repo_path / "keel-out"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / "rejections.yml"
    rejections = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else []
    rejections = rejections or []
    if contract_id not in rejections:
        rejections.append(contract_id)
    path.write_text(yaml.safe_dump(rejections, sort_keys=False), encoding="utf-8")


def save_proposals(repo_path: Path, proposals) -> Path:
    out_dir = repo_path / "keel-out"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / "proposals.yml"
    rejected = _load_rejections(repo_path)
    payload = [proposal_to_yaml(item) for item in proposals if item.id not in rejected]
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def load_proposals(repo_path: Path) -> list[dict]:
    path = repo_path / "keel-out" / "proposals.yml"
    if not path.exists():
        return []
    return yaml.safe_load(path.read_text(encoding="utf-8")) or []


def _load_rejections(repo_path: Path) -> set[str]:
    path = repo_path / "keel-out" / "rejections.yml"
    if not path.exists():
        return set()
    return set(yaml.safe_load(path.read_text(encoding="utf-8")) or [])
