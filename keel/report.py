from __future__ import annotations

from html import escape

from .models import ApprovedContract, CheckResult, ProposedContract, Violation


def render_discover(proposals: list[ProposedContract]) -> str:
    if not proposals:
        return "Keel found no candidate architecture contracts."
    lines = [f"Keel discovered {len(proposals)} candidate architecture contract(s).", ""]
    for proposal in proposals:
        lines.extend(
            [
                f"[{proposal.confidence}] {proposal.id}",
                proposal.title,
                "Evidence:",
                f"  {proposal.evidence.summary}",
                "Rule:",
                f"  {_rule_text(proposal.rule.kind, proposal.rule.params)}",
            ]
        )
        repair = proposal.repair.get("route_through_layer")
        if repair:
            lines.extend(["Repair:", f"  route through {repair}"])
        lines.extend(["Approve:", f"  keel approve {proposal.id} .", ""])
    return "\n".join(lines).rstrip()


def render_check(violations: list[Violation]) -> str:
    if not violations:
        return "Keel check passed. No architecture regressions found."
    lines = [f"Keel blocked {len(violations)} architecture regression(s).", ""]
    for index, violation in enumerate(violations, start=1):
        lines.append(f"{index}. {violation.message}")
        lines.append(f"   Contract: {violation.contract_id}")
        lines.append(f"   Rule: {violation.contract_title}")
        if violation.repair_hint:
            lines.append(f"   Repair: {violation.repair_hint}")
    return "\n".join(lines)


def render_check_result(result: CheckResult) -> str:
    lines = [render_check(result.blocking)]
    if result.known_debt:
        lines.extend(["", f"Known baseline debt: {len(result.known_debt)} violation(s)."])
        for index, violation in enumerate(result.known_debt, start=1):
            lines.append(f"{index}. {violation.message}")
            lines.append(f"   Contract: {violation.contract_id}")
    return "\n".join(lines)


def render_check_html(result: CheckResult) -> str:
    status = "failed" if result.blocking else "passed"
    sections = [
        "<!doctype html>",
        "<html><head><meta charset=\"utf-8\"><title>Keel Check Report</title>",
        "<style>body{font-family:system-ui,sans-serif;max-width:960px;margin:40px auto;padding:0 20px;line-height:1.45}"
        "h1{font-size:28px} .bad{color:#b00020}.good{color:#176b2c}.card{border:1px solid #ddd;padding:16px;margin:12px 0;border-radius:8px}"
        "code{background:#f5f5f5;padding:2px 4px;border-radius:4px}</style></head><body>",
        f"<h1>Keel check {escape(status)}</h1>",
    ]
    sections.append(_html_violation_section("Blocking regressions", result.blocking, "bad"))
    sections.append(_html_violation_section("Known baseline debt", result.known_debt, ""))
    sections.append("</body></html>")
    return "\n".join(sections)


def render_explain(contract: ApprovedContract) -> str:
    lines = [
        contract.id,
        contract.title,
        f"Status: {contract.status}",
        f"Source: {contract.source}",
        f"Rule: {_rule_text(contract.rule.kind, contract.rule.params)}",
        f"Evidence: {contract.evidence.summary}",
    ]
    if contract.repair:
        lines.append(f"Repair: {contract.repair}")
    return "\n".join(lines)


def render_replay(events: list[dict]) -> str:
    if not events:
        return "No events found for this session."
    lines = ["Keel replay:"]
    for event in events:
        lines.append(f"- {event.get('ts')} [{event.get('kind')}] {event.get('payload')}")
    return "\n".join(lines)


def _html_violation_section(title: str, violations: list[Violation], css_class: str) -> str:
    if not violations:
        return f"<h2>{escape(title)}</h2><p class=\"good\">None.</p>"
    rows = [f"<h2 class=\"{css_class}\">{escape(title)} ({len(violations)})</h2>"]
    for violation in violations:
        rows.append("<div class=\"card\">")
        rows.append(f"<p>{escape(violation.message)}</p>")
        rows.append(f"<p><strong>Contract:</strong> <code>{escape(violation.contract_id)}</code></p>")
        if violation.repair_hint:
            rows.append(f"<p><strong>Repair:</strong> {escape(violation.repair_hint)}</p>")
        rows.append("</div>")
    return "\n".join(rows)


def _rule_text(kind: str, params: dict) -> str:
    if kind == "forbid_edge":
        return f"forbid_edge from {params.get('from_layer')} to {params.get('to_layer')}"
    if kind == "allow_only_path":
        return "allow_only_path " + " -> ".join(params.get("route", []))
    if kind == "external_package_scope":
        return f"external_package_scope {params.get('package')}"
    if kind == "zone_ownership":
        return f"zone_ownership {params.get('zone')}"
    if kind == "no_cycles_between_layers":
        return "no_cycles_between_layers " + ", ".join(params.get("layers", []))
    return kind
