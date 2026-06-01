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
