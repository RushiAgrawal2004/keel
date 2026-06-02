# Build Keel Updates

## 2026-06-01 - Product Completion Pass

### Request
- Prepare Keel beyond the CLI MVP:
  - PyPI package readiness.
  - Hosted UI/dashboard readiness.
  - Full docs website.
  - GitHub Actions verification.
  - Better handling of Graphify graph-quality dependency.
  - PR bot comments.
  - ADR compiler.
  - Webhook governance integrations.
  - Richer HTML dashboards.

### Initial State
- Local git worktree was clean.
- `buildkeelupdates.md` did not exist and was created for ongoing build logs.
- Existing app already had CLI, Graphify integration, demo app, schemas, tests, and CI.

### Constraints
- Actual PyPI publishing requires a trusted publisher setup or `PYPI_API_TOKEN`.
- Actual hosted deployment requires a hosting target/token, such as GitHub Pages, Vercel, Netlify, or another platform.
- This pass will implement repo-ready workflows, generated site/dashboard artifacts, and local commands; external publication/deployment may still need user-side credentials.

### Changes
- Added PyPI package metadata to `pyproject.toml`: license, authors, keywords, classifiers, and project URLs.
- Added `.github/workflows/publish.yml` for release/manual PyPI publishing via trusted publishing.
- Verified package build with `python -m build` and `python -m twine check dist/*`; then updated license metadata to SPDX-style `license = "MIT"` to avoid setuptools deprecation warnings.
- Added `keel/graph_quality.py` to quantify Graphify graph health and warn about missing layers, ambiguous edges, and UNKNOWN layer coverage.
- Added `keel/dashboard.py` to generate a richer local HTML dashboard from checks, proposals, events, and graph-quality data.
- Added `docs/index.html` as a static documentation website.
- Added `.github/workflows/docs.yml` for GitHub Pages deployment of the docs site.
- Added `keel/pr_comment.py` for PR-ready markdown summaries of Keel check and graph quality.
- Added `keel/adr.py` to compile `docs/adr/*.md` YAML frontmatter into Keel contract YAML.
- Added `keel/webhook.py` to POST recent Keel events to governance/webhook systems.
- Extended `.github/workflows/keel.yml` to generate dashboards and PR comments when a Graphify graph is available.
- Added CLI commands: `keel graph-quality`, `keel dashboard`, `keel pr-comment`, `keel adr-compile`, and `keel webhook`.
- Added CLI tests covering dashboard generation, graph-quality JSON, PR comment generation, and ADR compilation.
- Updated `README.md` with dashboard, graph-quality, PR comment, ADR compiler, PyPI, and hosted docs guidance.
- Added `docs/adr/0001-ui-database-boundary.md` as a working ADR contract example.
- Added a local HTTP test for governance webhook POST export.

### Verification
- `python -m pytest` passed with 16 tests.
- `keel graph-quality demo-app --json` returned score `100` and status `ok`.
- `keel dashboard demo-app` wrote `demo-app/keel-out/dashboard.html`.
- `keel pr-comment demo-app` wrote `demo-app/keel-out/pr-comment.md`.
- `python -m build` created source and wheel distributions.
- `python -m twine check dist/*` passed for both generated distributions.
- Refreshed Graphify after the product-completion changes: `351 nodes`, `1033 edges`, `23 communities`.

## 2026-06-01 - External Build Guide Audit

### Request
- Compare the current Keel repo against `d:\microsoft apps\Keel-BUILD-GUIDE.md`.

### Findings
- The current repo implements a richer product track than the external guide in several areas: discovery, approvals, baseline support, dashboard, graph-quality checks, PR comments, ADR compilation, webhook export, PyPI workflow, docs workflow, and event memory.
- The current repo does not exactly satisfy the external guide's milestone layout.
- Missing guide-specific modules:
  - `keel/rules.py`
  - `keel/brief.py`
  - `keel/record.py`
  - `keel/serve.py`
- Missing guide-specific CLI commands:
  - `keel build`
  - `keel brief`
  - `keel replay`
- Missing guide-specific MCP dependency and server:
  - `mcp` is not in `pyproject.toml`.
  - No stdio MCP server exposes `get_brief`, `check_change`, `record_action`, or `get_replay`.
- The current config model uses `approved_contracts` and `ContractRule` rather than the guide's simpler `rules:` / `Rule` model.
- The current memory layer is `keel/memory.py` with `keel-out/keel.sqlite3`, while the guide asks for `record.py` with `keel-out/keel.db`, sessions, events, and replay.

### Conclusion
- Not everything from `Keel-BUILD-GUIDE.md` is built yet.
- The largest remaining guide milestones are M2 briefer, M3 MCP server, and M4 recorder/replay.

## 2026-06-01 - Guide-Specific Compatibility Build

### Request
- Build the missing external guide requirements:
  - `keel build`
  - `keel brief`
  - `keel replay`
  - `keel/rules.py`
  - `keel/brief.py`
  - `keel/record.py`
  - `keel/serve.py`
  - MCP server support.

### Planned Approach
- Keep the richer existing `approved_contracts` model intact.
- Add compatibility modules and commands that map existing approved contracts to guide-style deterministic rules.
- Add tests for build, brief, replay, rules, and MCP helper functions.

### Changes
- Added guide-compatible `Rule` dataclass and `Config.rules`.
- Added parser support for guide-style `.keel.yml` `rules:` entries.
- Added `keel/rules.py` with deterministic forbid and no-cycle checks.
- Added `keel/brief.py` for agent briefing markdown.
- Added `keel/record.py` with `keel-out/keel.db` sessions/events replay storage.
- Added `keel/serve.py` with MCP-facing helper functions and stdio server entrypoint.
- Added CLI commands: `keel build`, `keel brief`, `keel replay`, and `keel serve`.
- Added guide-focused fixtures and tests for rules, brief, build, replay, and MCP helper functions.
- Updated `check_repo_result` so guide-style `rules:` configs are enforced when no approved contracts are present.
- Updated `README.md` with guide-compatible `build`, `brief`, `replay`, and MCP server usage.
- Added `tests/fixtures/.keel.yml` so `keel check tests/fixtures` satisfies the guide's acceptance flow.

### Verification
- `python -m pytest` passed with 22 tests.
- `keel check tests\fixtures` produced exactly one UI -> DATABASE violation and exited with code 1.
- `python -m compileall keel` passed.
- `python -m pip install -e ".[dev]"` passed with `mcp` installed.
- `keel build demo-app` wrote `demo-app/keel-out/keel-graph.json`.
- `keel brief demo-app` printed the layer map, rules, graph counts, and agent instruction.
- `keel replay 999999 demo-app` handled an empty session cleanly.
- `keel serve --help` displayed the command help without starting the server.
- `python -m build` and `python -m twine check dist/*` passed.
- Refreshed Graphify after the guide-specific build: `418 nodes`, `1258 edges`, `29 communities`.

## 2026-06-01 - Plug-and-Play Install/MCP Flow

### Request
- Make Keel feel plug-and-play:
  - Install with pip.
  - Connect it to a codebase.
  - Use CLI or MCP for the same functionality.
  - Minimize hand wiring.

### Findings
- The exact PyPI package name `keel` is already occupied by an unrelated old package, so the command can be `keel`, but the distribution name likely needs to be something like `keel-arch` unless the PyPI name is transferred.
- The repo already has core CLI and MCP server support, but it lacks one-command onboarding and generated MCP config snippets.

### Planned Approach
- Add `keel doctor` for environment/repo readiness.
- Add `keel quickstart` for init/build/brief/dashboard guidance.
- Add preset-based `keel init --preset`.
- Add `keel mcp-config` to generate Codex/Claude/Cursor-style MCP snippets.

### Changes
- Added `keel/onboard.py` with presets, doctor checks, quickstart orchestration, and MCP config generation.
- Added CLI commands: `keel doctor`, `keel quickstart`, and `keel mcp-config`.
- Extended `keel init` with `--preset generic|python|node`.
- Updated `keel serve` so `--repo` works through the Typer command.
- Changed the publishable distribution name to `keel-arch` while keeping the import package and command name as `keel`, because PyPI already has an unrelated `keel` package.

### Verification
- `python -m pytest` passed with 23 tests.
- `keel doctor demo-app --json` reported the demo repo ready.
- `keel mcp-config demo-app --client codex` generated a Codex MCP server snippet.
- `keel quickstart demo-app --skip-graph --json` returned config, doctor, MCP, and next-step data.
- `keel serve --help` showed `--repo`.
- `python -m build` created `keel_arch-0.1.0` sdist and wheel.
- `python -m twine check dist/*` passed.
- Refreshed Graphify after plug-and-play onboarding changes: `434 nodes`, `1323 edges`, `31 communities`.

## 2026-06-01 - Docs Workflow Fix

### Request
- Fix the failing `Docs / deploy (push)` GitHub Actions check.

### Fix
- Changed `.github/workflows/docs.yml` so normal pushes only validate `docs/index.html`.
- Kept GitHub Pages deployment available, but only through manual `workflow_dispatch`.
- This avoids failed push checks when GitHub Pages has not been enabled/configured in repo settings yet.

### Verification
- Confirmed `docs/index.html` exists and is non-empty.
- `python -m pytest` passed with 23 tests.

## 2026-06-01 - Architecture Documentation

### Request
- Add an architecture file to the repo.

### Changes
- Added `ARCHITECTURE.md` at the repo root.
- Documented Keel's system flow, core concepts, modules, artifacts, contract lifecycle, rule types, MCP surface, CI setup, and design constraints.
- Linked `ARCHITECTURE.md` from `README.md`.

### Verification
- `python -m pytest` passed with 23 tests.
- Refreshed Graphify after adding architecture documentation: `440 nodes`, `1332 edges`, `30 communities`.

## 2026-06-02 - Agent Memory Engine

### Request
- Build Keel as a complex memory engine for Codex and Claude, not only an architecture checker.

### Changes
- Extended `keel/memory.py` with durable memory storage in `keel-out/keel.sqlite3`.
- Added memory operations: `remember`, `remember_project_context`, `recall`, `list_memories`, and `forget_memory`.
- Added CLI commands:
  - `keel remember`
  - `keel recall`
  - `keel memories`
  - `keel forget`
- Added MCP helper functions and server tools:
  - `memory_search`
  - `memory_write`
  - `memory_bootstrap`
- Updated README, architecture docs, and package metadata to frame Keel as persistent project memory plus architecture checks for coding agents.
- Added tests for memory storage, recall, bootstrap import, CLI commands, and MCP helper functions.

### Verification
- `python -m pytest` passed with 28 tests.
- `python -m build` created the `keel_arch-0.1.0` sdist and wheel.
- `python -m twine check dist/*` passed.
- Refreshed Graphify after memory-engine changes: `468 nodes`, `1490 edges`, `32 communities`.

## 2026-06-02 - Cognition Engine V1

### Request
- Build all major pieces needed for a benchmark-destroying memory/graph/coding-agent engine and explain what was built.

### Changes
- Upgraded memory storage with typed memory classification and encoding metadata.
- Added an optional encoding gate via `keel remember --gate` to reject low-signal memories.
- Added retrieval planning via `recall_plan()` and `keel recall --plan`.
- Added hybrid deterministic retrieval:
  - SQLite FTS5 when available.
  - keyword scoring across title, tags, source, and content.
  - memory-type targeting.
  - confidence weighting from encoding metadata.
- Added repo verification via `keel recall --verify`, including source-file and path existence checks.
- Added context pack generation via `keel context`.
- Added `keel/evals.py` and `keel eval` with a built-in memory benchmark that reports top-1, hit@5, MRR, and score percentage.
- Added `keel/hooks.py` and `keel hooks --client codex|claude|cursor|gemini|generic --write` to generate lifecycle hook configs for agent memory bootstrap, pre-task recall, and post-task capture.
- Added MCP memory context support through `mcp_memory_context`.
- Added tests for the encoding gate, retrieval planning, context packs, repo verification, eval command, hook config generation, and MCP memory context helper.

### Verification
- Targeted memory/CLI/MCP tests passed: `20 passed`.
- Full test suite passed: `30 passed`.
- `python -m build` created the `keel_arch-0.1.0` sdist and wheel with new modules included.
- `python -m twine check dist/*` passed.
- `python -m keel.cli eval . --json` produced `score_percent: 93.0`, `top1: 9/10`, `hit_at_5: 10/10`, `mrr: 0.95`.
- Refreshed Graphify after cognition-engine changes: `495 nodes`, `1611 edges`, `30 communities`.

## 2026-06-02 - Industry Memory Architecture

### Request
- Add a very good industry-level memory architecture to Keel.

### Changes
- Added `MEMORY_ARCHITECTURE.md` as a dedicated architecture specification for Keel's agent memory system.
- Added `keel/memory_architecture.py` with a structured blueprint for principles, layers, memory types, quality controls, and future layers.
- Added `keel memory-architecture` CLI command:
  - Prints the architecture blueprint as Markdown.
  - Supports `--json` for machine-readable output.
  - Supports `--write` to generate `keel-out/memory-architecture.md`.
- Linked the memory architecture from `README.md` and `ARCHITECTURE.md`.
- Extended CLI tests to cover the memory architecture command and output artifact.

### Verification
- `python -m pytest` passed with 30 tests.
- `python -m keel.cli memory-architecture . --json` printed the structured blueprint.
- `python -m keel.cli memory-architecture . --write` generated `keel-out/memory-architecture.md`.
- `python -m build` created the `keel_arch-0.1.0` sdist and wheel with `keel/memory_architecture.py` included.
- `python -m twine check dist/*` passed.
- Refreshed Graphify after memory architecture changes: `503 nodes`, `1659 edges`, `29 communities`.

## 2026-06-02 - Agent Project Manager Loop

### Request
- Make Keel connect to Claude Code through CLI/MCP setup and act like a project manager that keeps recording context and rebuilding the graph as the project proceeds.

### Changes
- Added `keel/manager.py` with `sync_project()`:
  - bootstraps project memory
  - optionally runs Graphify update
  - records a `project_synced` event in SQLite
- Added `keel/agent_setup.py`:
  - generates Claude Code/Codex/Cursor/Gemini/generic agent setup payloads
  - includes MCP config, lifecycle hook config, and manager instructions
- Added CLI commands:
  - `keel sync`
  - `keel agent-setup`
- Added MCP helper/tool:
  - `mcp_project_sync`
- Updated generated hook configs so session start uses `keel sync`.
- Updated README, architecture docs, and memory architecture docs with the project manager lifecycle.
- Added tests for CLI sync, Claude Code setup output, and MCP project sync helper.

### Verification
- Targeted CLI/MCP tests passed: `2 passed`.
- `python -m keel.cli agent-setup . --client claude-code --json` printed MCP config, hooks, and manager instructions.
- `python -m keel.cli sync . --no-graph --json` bootstrapped project memory and recorded a sync event.
- Full test suite passed: `31 passed`.
- `python -m build` created the `keel_arch-0.1.0` sdist and wheel with `keel/agent_setup.py` and `keel/manager.py` included.
- `python -m twine check dist/*` passed.
- First Graphify refresh attempt hit a temporary Gemini 503 high-demand error; retry succeeded.
- Refreshed Graphify after project-manager changes: `521 nodes`, `1719 edges`, `30 communities`.

## 2026-06-02 - Safe Context And Manager Health

### Request
- Continue hardening Keel core manager loop, SQLite memory, MCP setup, Claude/Codex lifecycle, safe context, evals, docs, packaging, and Graphify integration.

### Changes
- Added safe context behavior to `keel context`:
  - coverage labels (`HIGH`, `MEDIUM`, `LOW`)
  - safety instructions for agents
  - stale-memory warning
  - explicit fallback instructions when no memory matches
- Added `graph_status()` in `keel/graphify_runner.py`.
- Added `manager_status()` in `keel/manager.py`.
- Added CLI commands:
  - `keel manager-status`
  - `keel graph-status`
- Added MCP tools:
  - `mcp_project_status`
  - `mcp_graph_status`
- Added `MEMORY_ARCHITECTURE.md` capture to `remember_project_context()`.
- Updated hook configs and manager instructions to include status tools.
- Updated tests for safe context fallback, manager status, graph status, and MCP project status.

### Verification
- Targeted memory/CLI/MCP tests passed: `7 passed`.
- `python -m keel.cli context "totally unknown task" --repo . --limit 1` returned a low-coverage safe context pack.
- `python -m keel.cli manager-status . --json` reported memory, sync, and Graphify graph health.
- Full test suite passed: `32 passed`.
- `python -m build` created the `keel_arch-0.1.0` sdist and wheel.
- `python -m keel.cli graph-status . --json` reported the current Graphify graph status.
- `python -m twine check dist/*` passed.
- Refreshed Graphify after safe-context/status changes: `535 nodes`, `1787 edges`, `30 communities`.

## 2026-06-02 - Operations Guide

### Request
- Provide a file with step-by-step instructions for using Keel, monitoring Keel, testing Keel, and developing Keel further.

### Changes
- Added `KEEL_OPERATIONS_GUIDE.md`.
- Covered install, first setup, project sync, Claude Code/agent setup, safe context, memory operations, manager monitoring, Graphify monitoring, architecture rules, reports, user testing, developer testing, development workflow, roadmap, and debugging checklist.
- Linked `KEEL_OPERATIONS_GUIDE.md` from `README.md`.

### Verification
- `python -m pytest` passed with 32 tests.
- Refreshed Graphify after adding the operations guide: `544 nodes`, `1795 edges`, `32 communities`.

## 2026-06-02 - Friendly Graphify Failure Output

### Request
- Investigate scary Keel output from a test project where Graphify failed with `no LLM API key found`.

### Changes
- Added `GraphifyError` in `keel/graphify_runner.py`.
- Converted missing Graphify/API-key failures into clean, actionable messages.
- Hid Typer rich exception locals so Keel does not dump config objects, subprocess internals, or paths during normal CLI failures.
- Updated graph-dependent CLI commands to exit cleanly when Graphify is not ready.
- Added a CLI regression test for Graphify API-key failure output.

### Verification
- `python -m pytest` passed with 33 tests.
- First `graphify . --update` attempt failed because the shell had no provider key exported.
- Retried after loading `GEMINI_API_KEY` from `.env` without printing it.
- Refreshed Graphify after friendly-failure changes: `564 nodes`, `1834 edges`, `35 communities`.

## 2026-06-02 - Graphify `.env` Bootstrap

### Request
- When a Keel command needs Graphify and no API key is available, create a project `.env` preset for Gemini/OpenAI/Claude-style keys, then let the user rerun the same command.

### Changes
- Added project `.env` loading inside `keel/graphify_runner.py`.
- Keel now loads real Graphify provider keys from `.env` before running Graphify.
- If Graphify fails because no API key exists, Keel creates or updates `.env` with safe placeholder keys.
- Keel adds `.env` to the target repo `.gitignore` when it creates/updates the template.
- Keel retries Graphify automatically when a real key is available from `.env`.
- Added tests for friendly `.env` creation and automatic `.env` key loading.

### Verification
- `python -m pytest` passed with 34 tests.
- `python -m build` created the `keel_arch-0.1.0` sdist and wheel.
- Refreshed Graphify after `.env` bootstrap changes: `574 nodes`, `1892 edges`, `33 communities`.
