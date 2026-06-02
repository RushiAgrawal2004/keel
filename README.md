# Keel

Keel is a blackbox recorder for coding agents.

It gives Codex, Claude, and other MCP-compatible agents three focused capabilities:

- a Graphify project graph
- a command/session blackbox recorder
- an MCP server for agent access

## Quickstart

```bash
pip install keel-arch
keel init .
keel sync .
keel session-start . --label first-run
keel run "python -m pytest" --repo . --session 1
keel blackbox-note "Tests are the first verification gate." --repo . --session 1 --kind decision
keel blackbox-report 1 .
```

Keel reads and maintains `graphify-out/graph.json`, records command output and repo state into `keel-out/keel.db`, and exposes the same operations through MCP.

For the internal design, see [ARCHITECTURE.md](ARCHITECTURE.md), [MEMORY_ARCHITECTURE.md](MEMORY_ARCHITECTURE.md), and [KEEL_OPERATIONS_GUIDE.md](KEEL_OPERATIONS_GUIDE.md).

## Blackbox Recorder

```bash
keel sync .
keel session-start . --label claude
keel run "npm test" --repo . --session 1
keel run "npm run build" --repo . --session 1 --update-graph
keel blackbox-note "Build passes only after generated files are refreshed." --repo . --session 1 --kind finding
keel sessions .
keel blackbox-report 1 .
keel session-end 1 .
```

Every recorded command stores exit code, duration, stdout/stderr tails, output hashes, git status, changed files, diff stats, and Graphify graph status before/after the command.

## Commands

```bash
keel session-start . --label codex
keel run "python -m pytest" --repo . --session 1
keel blackbox-note "Important decision." --repo . --session 1 --kind decision
keel sessions .
keel blackbox-report 1 .
keel session-end 1 .
keel sync .
keel graph-status .
keel build .
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
keel manager-status .
keel graph-status .
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

- `mcp_project_sync`
- `mcp_project_status`
- `mcp_graph_status`
- `mcp_blackbox_start`
- `mcp_blackbox_run`
- `mcp_blackbox_note`
- `mcp_blackbox_sessions`
- `mcp_blackbox_report`
- `mcp_blackbox_end`
- `mcp_check_change`

Set `KEEL_REPO_PATH` or pass `--repo` to point the server at a target repo.

## Claude Code / Agent Manager Setup

```bash
keel agent-setup . --client claude-code --write
keel serve --repo .
```

This writes MCP setup and Keel manager instructions under `keel-out/agent-setup/`. The intended lifecycle is:

- session start: `keel session-start . --label claude-code` and `keel sync .`
- during work: `keel run "<command>" --repo . --session <id>`
- decisions: `keel blackbox-note "<decision>" --repo . --session <id> --kind decision`
- finish: `keel blackbox-report <id> .` and `keel session-end <id> .`

Use `keel manager-status .` and `keel graph-status .` to check whether memory, sync events, and Graphify outputs are healthy.

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
