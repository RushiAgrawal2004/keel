# Keel Architecture

Keel is a local-first memory engine and architecture governance tool for coding agents. It stores durable project memory for Codex, Claude, and other MCP-compatible agents, reads a Graphify knowledge graph for a repository, maps code nodes into configured layers and zones, proposes architecture contracts, and enforces only the contracts a human has approved.

The installed package name is `keel-arch`; the command users run is `keel`.

For the dedicated memory system design, see [MEMORY_ARCHITECTURE.md](MEMORY_ARCHITECTURE.md).

## Goals

- Make architecture rules executable without requiring users to manually model their whole codebase.
- Give coding agents durable recall across sessions and tools.
- Keep humans in control by separating discovered proposals from approved contracts.
- Support agent workflows through CLI output, JSON artifacts, reports, and an MCP server.
- Stay plug-and-play for a target repository: install, initialize, build, brief, check.

## System Flow

```text
target repo
  |
  | graphify . or keel build .
  v
graphify-out/graph.json
  |
  | load_graph()
  v
KeelGraph
  |
  | assign_layers_and_zones(.keel.yml)
  v
layered architecture graph
  |
  +--> discover_contracts() --> keel-out/proposals.yml --> approve/reject
  |
  +--> check_repo_result() --> CLI/JSON/HTML/PR comment/CI status
  |
  +--> make_brief() / MCP tools --> agent guidance
  |
  +--> remember_project_context() --> durable memory store --> recall/search
  |
  +--> eval/hooks/context --> benchmark loop + lifecycle automation
  |
  +--> dashboard/events/export --> human and integration artifacts
```

## Core Concepts

`Graphify graph`
: Source of truth for discovered nodes and edges. Keel expects `graphify-out/graph.json` by default.

`KeelGraph`
: Internal normalized graph containing code nodes, code connections, and external imports.

`Layer`
: A coarse architecture bucket such as `UI`, `SERVICE`, `DATABASE`, or `TEST`. Layers are assigned from path prefixes in `.keel.yml`.

`Zone`
: An ownership or domain boundary, also assigned from path prefixes in `.keel.yml`.

`Proposal`
: A contract Keel thinks may be true based on graph structure. Proposals are not enforced until approved.

`Approved contract`
: A human-approved architecture invariant stored in `.keel.yml`.

`Violation`
: A concrete graph edge, package import, zone access, or layer cycle that breaks an approved contract.

`Memory`
: A durable fact, preference, decision, project summary, graph summary, or session note stored in `keel-out/keel.sqlite3`.

`Encoding gate`
: A deterministic filter that classifies memory type, tags useful facts, and rejects low-signal memories when enabled.

`Context pack`
: A markdown bundle of the most relevant verified memories for an agent task.

## Main Modules

| Module | Responsibility |
| --- | --- |
| `keel/cli.py` | Typer CLI commands and command orchestration. |
| `keel/graphify_runner.py` | Locates or invokes Graphify and returns the graph path. |
| `keel/graph.py` | Converts Graphify JSON into `KeelGraph`. |
| `keel/layers.py` | Assigns nodes to layers and zones from config path prefixes. |
| `keel/config.py` | Loads, validates, and writes `.keel.yml`. |
| `keel/discover.py` | Mines candidate contracts from graph structure. |
| `keel/contracts.py` | Stores proposals and moves approved contracts into config. |
| `keel/check.py` | Evaluates approved contracts and baselines known debt. |
| `keel/rules.py` | Supports simpler legacy/manual rule checks. |
| `keel/repair.py` | Generates repair hints for violations. |
| `keel/report.py` | Renders CLI, HTML, explain, and replay output. |
| `keel/dashboard.py` | Builds local dashboard HTML. |
| `keel/brief.py` | Builds agent-facing architecture briefs. |
| `keel/record.py` and `keel/memory.py` | Track sessions, actions, events, durable memories, and recall in SQLite/JSONL. |
| `keel/memory_architecture.py` | Exposes the memory architecture blueprint as Markdown and JSON. |
| `keel/evals.py` | Runs built-in memory retrieval evaluations and writes benchmark output. |
| `keel/hooks.py` | Generates lifecycle hook configs for agent clients. |
| `keel/serve.py` | Exposes Keel over an MCP stdio server. |
| `keel/onboard.py` | Provides doctor, quickstart, presets, and MCP config snippets. |
| `keel/adr.py` | Compiles ADR frontmatter into contract artifacts. |
| `keel/pr_comment.py` | Writes pull request summary markdown. |
| `keel/webhook.py` | Sends governance export payloads to webhooks. |
| `keel/graph_quality.py` | Scores graph usefulness and warns about weak input graphs. |

## Data And Artifacts

| Path | Producer | Purpose |
| --- | --- | --- |
| `.keel.yml` | `keel init`, `keel approve`, or manual edit | Project config, layer/zone mapping, approved contracts. |
| `graphify-out/graph.json` | Graphify or `keel build` via Graphify | Raw knowledge graph input. |
| `graphify-out/GRAPH_REPORT.md` | Graphify | Human-readable graph analysis. |
| `keel-out/keel-graph.json` | `keel build` | Layered Keel graph snapshot. |
| `keel-out/proposals.yml` | `keel discover --write` | Candidate contracts awaiting approval. |
| `keel-out/baseline.yml` | `keel baseline` | Hashes of accepted existing violations. |
| `keel-out/check-report.html` | `keel check --html` | Human-readable check report. |
| `keel-out/dashboard.html` | `keel dashboard` | Local dashboard. |
| `keel-out/pr-comment.md` | `keel pr-comment` | Pull request comment body. |
| `keel-out/keel.sqlite3` | memory/event commands | Local event and durable memory database. |
| `keel-out/keel.db` | session commands | Local session replay database. |
| `keel-out/memory-eval.json` | `keel eval` | Built-in memory benchmark results. |
| `keel-out/memory-architecture.md` | `keel memory-architecture --write` | Generated memory architecture blueprint. |
| `keel-out/hooks/*.json` | `keel hooks --write` | Client lifecycle hook configs. |

## Memory Lifecycle

1. `keel remember --from-project --repo .` imports summaries from README, architecture docs, Graphify report, and `.keel.yml`.
2. `keel remember "fact" --kind decision --tag architecture` stores a manual memory.
3. `keel recall "question" --verify --plan` plans retrieval, searches memory, reranks matches, and verifies file-backed memories against the repo.
4. `keel context "task"` renders a compact memory context pack for an agent.
5. `keel memories` lists stored memories.
6. `keel forget MEMORY_ID` deletes a memory.
7. `keel eval` runs the built-in memory retrieval benchmark and writes `keel-out/memory-eval.json`.
8. `keel hooks --client codex --write` writes lifecycle hook config for automatic bootstrap, recall, and post-task memory capture.

Memory search is deterministic in v1: SQLite FTS when available, keyword scoring, type planning, confidence weighting, recency, and repo verification. A future semantic/vector search layer can sit on top of the same durable memory table.

## Contract Lifecycle

1. `keel init .` creates `.keel.yml`.
2. `graphify .` or `keel build .` ensures `graphify-out/graph.json` exists.
3. `keel discover . --write` mines candidate rules and writes `keel-out/proposals.yml`.
4. `keel proposals .` lists candidates.
5. `keel approve CONTRACT_ID .` moves a chosen contract into `.keel.yml`.
6. `keel check .` enforces approved contracts.
7. `keel baseline .` can mark existing known violations as accepted debt.

## Enforced Rule Types

- `forbid_edge`: forbids direct edges from one layer to another.
- `allow_only_path`: requires a source layer to reach a target layer through an approved route.
- `external_package_scope`: restricts a dependency package to allowed layers or zones.
- `zone_ownership`: restricts access into a zone to allowed owners.
- `no_cycles_between_layers`: prevents cycles in the configured layer graph.

## CLI Surfaces

Setup and onboarding:

```bash
keel init .
keel doctor .
keel quickstart .
keel mcp-config . --client codex
```

Graph and discovery:

```bash
keel build .
keel discover . --write
keel proposals .
keel approve CONTRACT_ID .
keel reject CONTRACT_ID .
```

Enforcement and reports:

```bash
keel check . --json --html
keel baseline .
keel explain CONTRACT_ID .
keel graph-quality .
keel dashboard .
keel pr-comment .
```

Agent and integration commands:

```bash
keel brief .
keel serve --repo .
keel replay SESSION_ID .
keel sync .
keel remember --from-project --repo .
keel recall "architecture rules" --repo . --verify --plan
keel context "architecture rules" --repo .
keel agent-setup . --client claude-code --write
keel memory-architecture . --write
keel eval .
keel hooks . --client codex --write
keel events .
keel export .
keel export-events .
keel adr-compile . --write
keel webhook URL .
```

## MCP Architecture

`keel serve --repo PATH` starts a stdio MCP server backed by the selected repository. It exposes:

- `mcp_get_brief`: returns the current architecture brief.
- `mcp_check_change`: checks a list of changed files for violations.
- `mcp_record_action`: records agent actions into the local replay log.
- `mcp_get_replay`: returns a rendered session replay.
- `mcp_memory_search`: recalls relevant durable memories.
- `mcp_memory_write`: stores a memory from an agent.
- `mcp_memory_bootstrap`: imports project context into memory.
- `mcp_memory_context`: returns a markdown memory context pack for an agent task.
- `mcp_project_sync`: bootstraps memory, refreshes the graph when available, and records a project sync event.

This makes Keel usable as a plug-and-play architecture guard for coding agents.

## CI Architecture

The GitHub Actions workflow in `.github/workflows/keel.yml` installs the package in editable mode, runs tests, and runs `keel check . --json --html` when `graphify-out/graph.json` exists. It also generates a PR comment body, dashboard, and uploaded report artifacts.

The docs workflow in `.github/workflows/docs.yml` validates `docs/index.html` on push. GitHub Pages deployment is manual through `workflow_dispatch` so normal pushes do not fail when Pages is not configured.

## Design Constraints

- Keel does not enforce unapproved proposals.
- Graph quality limits Keel quality; missing or noisy Graphify edges can affect proposals and checks.
- Layer and zone assignment is path-prefix based in v1.
- Keel is focused on project memory and architecture boundaries, not general code quality.
- Memory recall is deterministic hybrid retrieval in v1 and does not yet use embeddings or neural rerankers.
- Reports and dashboards are generated static artifacts so the tool works locally and in CI without a hosted backend.

## Development Map

```text
keel/
  cli.py              command entrypoint
  models.py           shared dataclasses
  config.py           .keel.yml parsing and validation
  graph.py            Graphify JSON adapter
  layers.py           layer and zone assignment
  discover.py         contract mining
  check.py            contract enforcement
  report.py           text and HTML rendering
  serve.py            MCP server
  onboard.py          plug-and-play onboarding
tests/
  test_*.py           behavior and CLI coverage
demo-app/
  src/                sample app used to demonstrate boundaries
docs/
  index.html          static documentation site
```
