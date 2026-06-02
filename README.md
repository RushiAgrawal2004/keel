# Keel

Keel is a memory engine for coding agents.

It gives Codex, Claude, and other MCP-compatible agents durable project memory, architecture context, session replay, and architecture regression checks powered by Graphify.

## Quickstart

```bash
pip install keel-arch
keel init .
keel discover . --write
keel proposals .
keel approve ui_never_touches_database .
keel check .
```

Keel reads `graphify-out/graph.json`, proposes deterministic architecture contracts from the graph, and enforces only contracts a human approved in `.keel.yml`.

For the internal design, see [ARCHITECTURE.md](ARCHITECTURE.md) and [MEMORY_ARCHITECTURE.md](MEMORY_ARCHITECTURE.md).

## Agent Memory

```bash
keel remember --from-project --repo .
keel remember "Always update buildkeelupdates.md after Keel changes." --kind preference --tag agent
keel sync .
keel recall "how do I run tests?" --repo . --verify --plan
keel context "debug the dashboard" --repo .
keel agent-setup . --client claude-code --write
keel memory-architecture . --write
keel memories --repo .
keel eval .
keel hooks . --client codex --write
```

Keel stores durable memory in `keel-out/keel.sqlite3`. Memories can be project summaries, architecture notes, user preferences, decisions, session facts, or any other context an agent should remember across runs.

The memory engine includes a deterministic encoding gate, typed memory classification, SQLite FTS-backed retrieval when available, query planning, reranking signals, repo verification, context-pack rendering, lifecycle hook configs, and a built-in memory eval suite.

## Commands

```bash
keel discover . --json
keel proposals .
keel approve ui_never_touches_database .
keel check . --json --html
keel baseline .
keel build .
keel brief .
keel replay SESSION_ID .
keel remember "Run tests with python -m pytest." --kind project
keel sync .
keel recall "tests"
keel context "architecture boundaries"
keel agent-setup . --client claude-code --write
keel memory-architecture .
keel eval .
keel hooks . --client codex --write
keel events .
keel export-events .
keel export . --format json
keel graph-quality . --json
keel dashboard .
keel pr-comment .
keel adr-compile . --write
```

`keel check` exits `1` only for new blocking violations. Violations captured by `keel baseline` are reported as known debt.

## Demo

```powershell
.\scripts\demo.ps1
```

The demo maps `demo-app`, discovers `UI must not access DATABASE directly`, approves it, and runs a clean architecture check.

## Agent And CI Integration

Keel exposes stable JSON for adapters:

- `keel discover . --json`
- `keel check . --json`
- `keel explain CONTRACT_ID . --json`
- `keel export . --format json`
- `keel export-events .`

The GitHub Actions workflow in `.github/workflows/keel.yml` runs tests and `keel check . --json --html`.

## Agent Briefing And MCP

```bash
keel build .
keel brief .
keel serve
```

`keel build` writes a layered graph snapshot to `keel-out/keel-graph.json`. `keel brief` prints a short markdown briefing for coding agents. `keel serve` starts a stdio MCP server exposing:

- `get_brief`
- `check_change`
- `record_action`
- `get_replay`
- `memory_search`
- `memory_write`
- `memory_bootstrap`
- `memory_context`
- `project_sync`

Set `KEEL_REPO_PATH` or pass `--repo` to point the server at a target repo.

## Claude Code / Agent Manager Setup

```bash
keel agent-setup . --client claude-code --write
keel serve --repo .
```

This writes MCP setup and Keel manager instructions under `keel-out/agent-setup/`. The intended lifecycle is:

- session start: `keel sync .`
- before task: `keel context "<task>"`
- after task: `keel remember "<summary>" --kind session --tag agent --gate`
- finish: run tests, `keel check .`, and `keel eval .`

## Plug-And-Play Setup

The PyPI distribution is `keel-arch` because the exact `keel` package name is already taken on PyPI. The installed command is still `keel`.

```bash
pip install keel-arch
keel quickstart /path/to/repo --preset generic
keel doctor /path/to/repo
keel mcp-config /path/to/repo --client codex
```

## Dashboard And Reports

```bash
keel dashboard .
keel graph-quality .
keel pr-comment .
```

These commands generate local HTML and Markdown artifacts under `keel-out/` for humans, pull requests, and CI artifacts.

## ADR Compiler

Add ADR files under `docs/adr/*.md` with YAML frontmatter:

```yaml
---
keel_contract:
  id: ui_never_touches_database
  title: UI must not access DATABASE directly
  rule:
    forbid_edge:
      from_layer: UI
      to_layer: DATABASE
      relation: "*"
---
```

Then run:

```bash
keel adr-compile . --write
```

## PyPI And Hosted Docs

The repo includes:

- `.github/workflows/publish.yml` for PyPI publishing from GitHub releases or manual workflow dispatch.
- `.github/workflows/docs.yml` for GitHub Pages deployment from `docs/`.

Publishing requires configuring PyPI trusted publishing or an equivalent repository secret.

## Limitations

- Keel depends on Graphify's graph quality.
- Keel proposes likely invariants, not universal truths.
- Human approval is required before enforcement.
- Layer and zone assignment are folder-based in v1.
- Keel is not a general code quality reviewer and does not replace tests.
