from __future__ import annotations

from pathlib import Path

import yaml


def compile_adr_contracts(repo_path: Path, write: bool = False) -> list[dict]:
    adr_dir = repo_path / "docs" / "adr"
    contracts: list[dict] = []
    if not adr_dir.exists():
        return contracts
    for path in sorted(adr_dir.glob("*.md")):
        frontmatter = _frontmatter(path)
        contract = frontmatter.get("keel_contract")
        if isinstance(contract, dict):
            contract.setdefault("source", "adr")
            contract.setdefault("status", "approved")
            contract.setdefault("evidence", {})
            contract["evidence"].setdefault("summary", f"Compiled from ADR {path.name}.")
            contracts.append(contract)
    if write:
        out_dir = repo_path / "keel-out"
        out_dir.mkdir(exist_ok=True)
        (out_dir / "adr-contracts.yml").write_text(yaml.safe_dump(contracts, sort_keys=False), encoding="utf-8")
    return contracts


def _frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}

