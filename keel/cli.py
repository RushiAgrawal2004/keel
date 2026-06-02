from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Annotated

import typer

from .brief import make_brief
from .check import check_repo_result, write_baseline
from .config import default_config, load_config, save_config
from .contracts import approve_contract, load_proposals, reject_contract, save_proposals
from .adr import compile_adr_contracts
from .dashboard import build_dashboard
from .discover import discover_contracts
from .graph import load_graph
from .graph_quality import graph_quality
from .graphify_runner import ensure_graph
from .layers import assign_layers_and_zones
from .memory import (
    context_pack,
    export_events_jsonl,
    forget_memory,
    list_events,
    list_memories,
    recall as recall_memories,
    recall_plan,
    record_event,
    remember as remember_memory,
    remember_project_context,
)
from .memory_architecture import memory_architecture as memory_architecture_spec
from .memory_architecture import render_memory_architecture, write_memory_architecture
from .evals import run_memory_eval
from .hooks import hook_config, write_hook_config
from .onboard import doctor as run_doctor
from .onboard import mcp_config, pretty_json, quickstart as run_quickstart
from .onboard import write_preset_config
from .pr_comment import write_pr_comment
from .record import get_session
from .report import render_check_html, render_check_result, render_discover, render_explain, render_replay
from .serve import main as serve_main
from .webhook import send_governance_webhook

app = typer.Typer(no_args_is_help=True)


@app.command()
def build(path: Annotated[Path, typer.Argument()] = Path(".")) -> None:
    repo = path.resolve()
    config = load_config(repo)
    graph = load_graph(ensure_graph(repo))
    assign_layers_and_zones(graph, config)
    out_dir = repo / "keel-out"
    out_dir.mkdir(exist_ok=True)
    layer_counts: dict[str, int] = {}
    for node in graph.nodes.values():
        layer_counts[node.layer] = layer_counts.get(node.layer, 0) + 1
    payload = {
        "nodes": [asdict(node) for node in graph.nodes.values()],
        "connections": [asdict(connection) for connection in graph.connections],
        "layers": layer_counts,
    }
    out = out_dir / "keel-graph.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    typer.echo(f"Built Keel graph: {len(graph.nodes)} nodes, {len(graph.connections)} connections")
    for layer, count in sorted(layer_counts.items()):
        typer.echo(f"  {layer}: {count}")
    typer.echo(f"Wrote {out}")


@app.command()
def init(
    path: Annotated[Path, typer.Argument()] = Path("."),
    force: Annotated[bool, typer.Option("--force", help="Overwrite an existing .keel.yml.")] = False,
    preset: Annotated[str, typer.Option("--preset", help="Layer/rule preset: generic, python, or node.")] = "generic",
) -> None:
    target = path.resolve()
    config_path = target / ".keel.yml"
    if config_path.exists() and not force:
        raise typer.BadParameter(".keel.yml already exists. Use --force to overwrite.")
    write_preset_config(target, preset, force=True)
    typer.echo(f"Wrote {config_path}")


@app.command()
def doctor(
    path: Annotated[Path, typer.Argument()] = Path("."),
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    result = run_doctor(path.resolve())
    if json_output:
        typer.echo(pretty_json(result))
        return
    typer.echo("Keel doctor")
    for check in result["checks"]:
        mark = "OK" if check["ok"] else "MISSING"
        typer.echo(f"- {mark}: {check['name']} ({check['detail']})")
    raise typer.Exit(0 if result["ok"] else 1)


@app.command()
def quickstart(
    path: Annotated[Path, typer.Argument()] = Path("."),
    preset: Annotated[str, typer.Option("--preset", help="Layer/rule preset: generic, python, or node.")] = "generic",
    force: Annotated[bool, typer.Option("--force", help="Overwrite an existing .keel.yml.")] = False,
    skip_graph: Annotated[bool, typer.Option("--skip-graph", help="Do not run Graphify during setup.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    result = run_quickstart(path.resolve(), preset=preset, force=force, skip_graph=skip_graph)
    if json_output:
        typer.echo(pretty_json(result))
        return
    typer.echo(f"Keel config: {result['config_path']}")
    if result["graph_path"]:
        typer.echo(f"Graphify graph: {result['graph_path']}")
    if result["graph_error"]:
        typer.echo(f"Graphify not ready: {result['graph_error']}")
    typer.echo("Next commands:")
    for item in result["next"]:
        typer.echo(f"  {item}")


@app.command("mcp-config")
def mcp_config_command(
    path: Annotated[Path, typer.Argument()] = Path("."),
    client: Annotated[str, typer.Option("--client", help="codex, claude, or cursor.")] = "codex",
) -> None:
    typer.echo(pretty_json(mcp_config(path.resolve(), client)))


@app.command()
def discover(
    path: Annotated[Path, typer.Argument()] = Path("."),
    write: Annotated[bool, typer.Option("--write", help="Write proposals to keel-out/proposals.yml.")] = False,
    include_low: Annotated[bool, typer.Option("--include-low", help="Include low-confidence proposals.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    repo = path.resolve()
    config = load_config(repo)
    graph = load_graph(ensure_graph(repo))
    assign_layers_and_zones(graph, config)
    proposals = discover_contracts(graph, config, include_low=include_low)
    if write:
        save_proposals(repo, proposals)
        record_event(repo, "proposals_written", {"count": len(proposals), "path": "keel-out/proposals.yml"})
    record_event(repo, "discover", {"proposal_count": len(proposals), "include_low": include_low, "wrote_file": write})
    if json_output:
        typer.echo(json.dumps([_proposal_payload(item) for item in proposals], indent=2))
    else:
        typer.echo(render_discover(proposals))


@app.command()
def proposals(
    path: Annotated[Path, typer.Argument()] = Path("."),
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    items = load_proposals(path.resolve())
    if json_output:
        typer.echo(json.dumps(items, indent=2))
    elif not items:
        typer.echo("No stored proposals. Run `keel discover . --write` first.")
    else:
        for item in items:
            typer.echo(f"[{item.get('confidence')}] {item.get('id')} - {item.get('title')}")


@app.command()
def approve(contract_id: Annotated[str, typer.Argument()], path: Annotated[Path, typer.Argument()] = Path(".")) -> None:
    repo = path.resolve()
    approved = approve_contract(repo, contract_id)
    record_event(repo, "contract_approved", {"contract_id": approved.id, "title": approved.title})
    typer.echo(f"Approved {approved.id}")


@app.command()
def reject(contract_id: Annotated[str, typer.Argument()], path: Annotated[Path, typer.Argument()] = Path(".")) -> None:
    repo = path.resolve()
    reject_contract(repo, contract_id)
    record_event(repo, "contract_rejected", {"contract_id": contract_id})
    typer.echo(f"Rejected {contract_id}")


@app.command()
def check(
    path: Annotated[Path, typer.Argument()] = Path("."),
    changed: Annotated[list[str] | None, typer.Option("--changed", help="Only report violations involving these files.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
    html: Annotated[bool, typer.Option("--html", help="Write keel-out/check-report.html.")] = False,
) -> None:
    repo = path.resolve()
    result = check_repo_result(repo, changed_files=changed)
    if html:
        out_dir = repo / "keel-out"
        out_dir.mkdir(exist_ok=True)
        (out_dir / "check-report.html").write_text(render_check_html(result), encoding="utf-8")
    record_event(
        repo,
        "check",
        {
            "blocking_count": len(result.blocking),
            "known_debt_count": len(result.known_debt),
            "changed_files": changed or [],
            "html": html,
        },
    )
    if json_output:
        typer.echo(json.dumps(_check_payload(result), indent=2))
    else:
        typer.echo(render_check_result(result))
    if result.blocking:
        raise typer.Exit(1)


@app.command()
def brief(path: Annotated[Path, typer.Argument()] = Path(".")) -> None:
    repo = path.resolve()
    config = load_config(repo)
    graph = load_graph(ensure_graph(repo))
    assign_layers_and_zones(graph, config)
    typer.echo(make_brief(graph, config))


@app.command()
def replay(session_id: Annotated[int, typer.Argument()], path: Annotated[Path, typer.Argument()] = Path(".")) -> None:
    typer.echo(render_replay(get_session(path.resolve(), session_id)))


@app.command()
def remember(
    content: Annotated[str | None, typer.Argument(help="Memory text to store.")] = None,
    repo: Annotated[Path, typer.Option("--repo", help="Repository path for the memory store.")] = Path("."),
    kind: Annotated[str, typer.Option("--kind", help="Memory kind, such as project, architecture, decision, preference, or session.")] = "note",
    title: Annotated[str | None, typer.Option("--title", help="Short title for this memory.")] = None,
    tag: Annotated[list[str] | None, typer.Option("--tag", help="Tag to attach. Can be used multiple times.")] = None,
    from_project: Annotated[bool, typer.Option("--from-project", help="Import README, architecture, Graphify report, and .keel.yml summaries.")] = False,
    gate: Annotated[bool, typer.Option("--gate", help="Use the encoding gate and reject low-signal memories.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    path = repo.resolve()
    if from_project:
        ids = remember_project_context(path)
        payload = {"stored": ids, "count": len(ids)}
        typer.echo(json.dumps(payload, indent=2) if json_output else f"Stored {len(ids)} project memory item(s).")
        return
    if not content:
        raise typer.BadParameter("Provide memory text or use --from-project.")
    memory_id = remember_memory(path, content, kind=kind, title=title, tags=tag or [], gate=gate)
    if memory_id == 0:
        typer.echo("Memory rejected by encoding gate.")
        return
    payload = {"id": memory_id, "kind": kind, "title": title or content[:80]}
    typer.echo(json.dumps(payload, indent=2) if json_output else f"Remembered memory #{memory_id}.")


@app.command()
def recall(
    query: Annotated[str, typer.Argument(help="Question or keywords to recall memories for.")],
    repo: Annotated[Path, typer.Option("--repo", help="Repository path for the memory store.")] = Path("."),
    limit: Annotated[int, typer.Option("--limit", help="Maximum memories to return.")] = 5,
    kind: Annotated[str | None, typer.Option("--kind", help="Only recall this memory kind.")] = None,
    tag: Annotated[list[str] | None, typer.Option("--tag", help="Require tag. Can be used multiple times.")] = None,
    verify: Annotated[bool, typer.Option("--verify", help="Verify recalled memory against files in the repo.")] = False,
    show_plan: Annotated[bool, typer.Option("--plan", help="Show retrieval plan.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    path = repo.resolve()
    memories = recall_memories(path, query, limit=limit, kind=kind, tags=tag or [], verify=verify)
    if json_output:
        payload = {"plan": recall_plan(query), "memories": memories} if show_plan else memories
        typer.echo(json.dumps(payload, indent=2))
        return
    if show_plan:
        typer.echo(json.dumps(recall_plan(query), indent=2))
    if not memories:
        typer.echo("No matching memories found.")
        return
    for item in memories:
        typer.echo(f"[{item['score']}] #{item['id']} {item['kind']} - {item['title']}")
        typer.echo(f"source: {item['source']} tags: {', '.join(item['tags']) or '-'}")
        typer.echo(f"channels: {', '.join(item.get('channels', [])) or '-'}")
        if verify:
            typer.echo(f"verification: {item.get('verification', {}).get('status', 'unknown')}")
        typer.echo(item["content"])
        typer.echo("")


@app.command("memories")
def memories_command(
    repo: Annotated[Path, typer.Option("--repo", help="Repository path for the memory store.")] = Path("."),
    limit: Annotated[int, typer.Option("--limit", help="Maximum memories to show.")] = 20,
    kind: Annotated[str | None, typer.Option("--kind", help="Only list this memory kind.")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    memories = list_memories(repo.resolve(), limit=limit, kind=kind)
    if json_output:
        typer.echo(json.dumps(memories, indent=2))
        return
    if not memories:
        typer.echo("No memories stored yet.")
        return
    for item in memories:
        typer.echo(f"#{item['id']} {item['kind']} - {item['title']} ({item['source']})")


@app.command("forget")
def forget_command(
    memory_id: Annotated[int, typer.Argument(help="Memory id to delete.")],
    repo: Annotated[Path, typer.Option("--repo", help="Repository path for the memory store.")] = Path("."),
) -> None:
    if not forget_memory(repo.resolve(), memory_id):
        raise typer.BadParameter(f"Memory not found: {memory_id}")
    typer.echo(f"Forgot memory #{memory_id}.")


@app.command("context")
def context_command(
    query: Annotated[str, typer.Argument(help="Question or task to build a memory context pack for.")],
    repo: Annotated[Path, typer.Option("--repo", help="Repository path for the memory store.")] = Path("."),
    limit: Annotated[int, typer.Option("--limit", help="Maximum memories to include.")] = 6,
) -> None:
    typer.echo(context_pack(repo.resolve(), query, limit=limit))


@app.command("memory-architecture")
def memory_architecture_command(
    path: Annotated[Path, typer.Argument(help="Repository path. Used when writing output.")] = Path("."),
    write: Annotated[bool, typer.Option("--write", help="Write keel-out/memory-architecture.md.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    repo = path.resolve()
    if json_output:
        typer.echo(json.dumps(memory_architecture_spec(), indent=2))
        return
    if write:
        out = write_memory_architecture(repo)
        typer.echo(f"Wrote {out}")
        return
    typer.echo(render_memory_architecture())


@app.command("eval")
def eval_command(
    path: Annotated[Path, typer.Argument(help="Repository path. Used for output location.")] = Path("."),
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    result = run_memory_eval(path.resolve())
    out_dir = path.resolve() / "keel-out"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "memory-eval.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    if json_output:
        typer.echo(json.dumps(result, indent=2))
        return
    typer.echo(f"Keel memory eval: {result['score_percent']}%")
    typer.echo(f"top1={result['top1']}/{result['cases']} hit@5={result['hit_at_5']}/{result['cases']} mrr={result['mrr']}")
    typer.echo(f"Wrote {out_path}")


@app.command("hooks")
def hooks_command(
    path: Annotated[Path, typer.Argument(help="Repository path.")] = Path("."),
    client: Annotated[str, typer.Option("--client", help="codex, claude, cursor, gemini, or generic.")] = "codex",
    write: Annotated[bool, typer.Option("--write", help="Write keel-out/hooks/<client>-hooks.json.")] = False,
) -> None:
    repo = path.resolve()
    config = write_hook_config(repo, client) if write else hook_config(repo, client)
    typer.echo(json.dumps(config, indent=2))


@app.command()
def serve(path: Annotated[Path, typer.Option("--repo", help="Repository path to serve over MCP.")] = Path(".")) -> None:
    serve_main(["--repo", str(path.resolve())])


@app.command()
def baseline(path: Annotated[Path, typer.Argument()] = Path(".")) -> None:
    repo = path.resolve()
    baseline_path = write_baseline(repo)
    record_event(repo, "baseline_written", {"path": str(baseline_path.relative_to(repo))})
    typer.echo(f"Wrote {baseline_path}")


@app.command()
def explain(
    contract_id: Annotated[str, typer.Argument()],
    path: Annotated[Path, typer.Argument()] = Path("."),
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    config = load_config(path.resolve())
    contract = next((item for item in config.approved_contracts if item.id == contract_id), None)
    if not contract:
        raise typer.BadParameter(f"Contract not found: {contract_id}")
    if json_output:
        typer.echo(json.dumps(asdict(contract), indent=2))
    else:
        typer.echo(render_explain(contract))


@app.command("export")
def export_data(
    path: Annotated[Path, typer.Argument()] = Path("."),
    format: Annotated[str, typer.Option("--format", help="Currently only json is supported.")] = "json",
) -> None:
    if format != "json":
        raise typer.BadParameter("Only --format json is supported")
    repo = path.resolve()
    config = load_config(repo)
    payload = {
        "config": {
            "version": config.version,
            "project": config.project,
            "graph": config.graph,
            "layers": config.layers,
            "zones": config.zones,
            "ignore": config.ignore,
            "approved_contracts": [asdict(item) for item in config.approved_contracts],
        },
        "proposals": load_proposals(repo),
        "events": list_events(repo, limit=100),
    }
    typer.echo(json.dumps(payload, indent=2))


@app.command()
def events(
    path: Annotated[Path, typer.Argument()] = Path("."),
    limit: Annotated[int, typer.Option("--limit", help="Maximum events to show.")] = 50,
) -> None:
    typer.echo(json.dumps(list_events(path.resolve(), limit=limit), indent=2))


@app.command("export-events")
def export_events(
    path: Annotated[Path, typer.Argument()] = Path("."),
    output: Annotated[Path | None, typer.Option("--output", help="Output JSONL path.")] = None,
) -> None:
    repo = path.resolve()
    out = export_events_jsonl(repo, output)
    typer.echo(f"Wrote {out}")


@app.command("graph-quality")
def graph_quality_command(
    path: Annotated[Path, typer.Argument()] = Path("."),
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    quality = graph_quality(path.resolve())
    record_event(path.resolve(), "graph_quality", {"score": quality["score"], "status": quality["status"]})
    if json_output:
        typer.echo(json.dumps(quality, indent=2))
        return
    typer.echo(f"Graph quality: {quality['score']}/100 ({quality['status']})")
    for warning in quality.get("warnings", []):
        typer.echo(f"- {warning}")


@app.command()
def dashboard(
    path: Annotated[Path, typer.Argument()] = Path("."),
    output: Annotated[Path | None, typer.Option("--output", help="Dashboard HTML output path.")] = None,
) -> None:
    repo = path.resolve()
    out = build_dashboard(repo, output)
    record_event(repo, "dashboard_written", {"path": str(out)})
    typer.echo(f"Wrote {out}")


@app.command("pr-comment")
def pr_comment(
    path: Annotated[Path, typer.Argument()] = Path("."),
    output: Annotated[Path | None, typer.Option("--output", help="PR comment markdown output path.")] = None,
) -> None:
    repo = path.resolve()
    out = write_pr_comment(repo, output)
    record_event(repo, "pr_comment_written", {"path": str(out)})
    typer.echo(f"Wrote {out}")


@app.command("adr-compile")
def adr_compile(
    path: Annotated[Path, typer.Argument()] = Path("."),
    write: Annotated[bool, typer.Option("--write", help="Write keel-out/adr-contracts.yml.")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON.")] = False,
) -> None:
    repo = path.resolve()
    contracts = compile_adr_contracts(repo, write=write)
    record_event(repo, "adr_compile", {"contract_count": len(contracts), "wrote_file": write})
    if json_output:
        typer.echo(json.dumps(contracts, indent=2))
    elif write:
        typer.echo(f"Wrote {repo / 'keel-out' / 'adr-contracts.yml'}")
    else:
        typer.echo(f"Compiled {len(contracts)} ADR contract(s).")


@app.command("webhook")
def webhook(
    url: Annotated[str, typer.Argument()],
    path: Annotated[Path, typer.Argument()] = Path("."),
    event_type: Annotated[str, typer.Option("--event-type", help="Webhook event type.")] = "keel.export",
) -> None:
    repo = path.resolve()
    response = send_governance_webhook(repo, url, event_type=event_type)
    record_event(repo, "webhook_sent", {"url": url, "status": response["status"]})
    typer.echo(json.dumps(response, indent=2))


def _proposal_payload(proposal) -> dict:
    payload = asdict(proposal)
    payload["rule"] = {proposal.rule.kind: proposal.rule.params}
    return payload


def _check_payload(result) -> dict:
    return {
        "status": "failed" if result.blocking else "passed",
        "blocking": [asdict(item) for item in result.blocking],
        "known_debt": [asdict(item) for item in result.known_debt],
    }


if __name__ == "__main__":
    app()
