# Keel Build Guide V2

Keel is an architecture invariant miner and regression test runner for AI-generated code.

Graphify maps the repository. Keel studies that graph, discovers the unwritten architectural
rules the codebase already follows, asks a human to approve those rules, and then enforces them
as deterministic tests forever.

The product is not "another context layer." The product is:

> Keel finds the unwritten rules of your codebase and makes them executable.

Or, shorter:

> Architecture regression tests for AI-generated code.

---

## 1. The Problem

AI coding agents often produce code that is locally reasonable:

- tests pass
- types pass
- the feature works
- the diff looks clean

But the change can still quietly damage the architecture:

- a React component imports Prisma directly
- an API route skips the service layer
- payment code starts spreading outside billing modules
- auth token handling appears in unrelated files
- migrations import runtime app code
- background jobs start depending on UI code

The hard part is that these rules are often not written down. They live in the existing
shape of the codebase.

Keel's job is to extract those implicit rules, make them reviewable, and enforce them.

---

## 2. Core Loop

```text
1. Graphify maps the repo.
2. Keel discovers stable architectural invariants.
3. Keel proposes candidate contracts with evidence.
4. Human approves useful contracts.
5. Keel writes approved contracts to .keel.yml.
6. AI agents and CI run keel check.
7. Keel blocks architecture regressions and gives repair hints.
```

Keel never silently invents law. It proposes. A human approves. Then Keel enforces.

---

## 3. Product Boundary

### 3.1 Graphify

Graphify answers:

```text
What exists in this repository?
What files, symbols, relationships, imports, calls, and code entities are connected?
```

Keel relies on Graphify for the code graph. Keel does not parse source code directly in v1.

### 3.2 Keel

Keel answers:

```text
What architectural invariants does this repository appear to follow?
Which of those should become executable contracts?
Did this change break any approved contract?
How should the agent repair the violation?
```

### 3.3 Optional Governance Layer

Tools like GovForge-style systems answer:

```text
Who approved this?
What was the audit trail?
Which high-risk decisions require human approval?
```

Keel can export events to such a layer later, but it must not depend on one for v1.

---

## 4. Non-Negotiable Rules

1. Keel must not reimplement code parsing.
2. Keel must use Graphify output as the source of graph truth.
3. Keel must not call an LLM to decide whether a violation exists.
4. Keel may use heuristics to propose contracts, but approved checks must be deterministic.
5. Keel must not enforce discovered contracts until a human approves them.
6. `keel check` must exit code `1` when approved contracts are violated.
7. Every proposed contract must include evidence.
8. Every violation must include provenance: which approved contract was violated.
9. Every violation should include a deterministic repair hint when possible.
10. Build the CLI first. Agent/MCP integration is outsourced and should use Keel's JSON output.

---

## 5. Tech Stack

- Python 3.11+
- `uv`
- `typer` for CLI
- `pydantic` v2 for config validation
- `pyyaml` for `.keel.yml`
- `networkx` for graph algorithms
- `pytest` for tests
- MCP is not a core dependency. Agent integration should be handled by an external adapter.
- SQLite for local event/audit store in later milestones

Project entry point:

```toml
[project.scripts]
keel = "keel.cli:app"
```

---

## 6. Repository Layout

Create exactly this structure:

```text
keel/
  pyproject.toml
  README.md
  .keel.yml
  keel/
    __init__.py
    models.py
    config.py
    graphify_runner.py
    graph.py
    layers.py
    discover.py
    contracts.py
    check.py
    repair.py
    report.py
    cli.py
    memory.py
  tests/
    fixtures/
      sample_graph.json
      sample_clean_graph.json
      sample_regressed_graph.json
      sample.keel.yml
    test_config.py
    test_graph.py
    test_layers.py
    test_discover.py
    test_contracts.py
    test_check.py
    test_repair.py
    test_cli.py
```

---

## 7. Graph Input

Keel reads Graphify NetworkX node-link JSON.

Example:

```json
{
  "directed": true,
  "multigraph": false,
  "graph": {},
  "nodes": [
    {
      "id": "src/components/Dashboard.tsx::Dashboard",
      "label": "Dashboard",
      "file_type": "code",
      "source_file": "src/components/Dashboard.tsx"
    },
    {
      "id": "src/db/users.ts::getUserById",
      "label": "getUserById",
      "file_type": "code",
      "source_file": "src/db/users.ts"
    }
  ],
  "links": [
    {
      "source": "src/components/Dashboard.tsx::Dashboard",
      "target": "src/db/users.ts::getUserById",
      "relation": "imports",
      "confidence": "EXTRACTED"
    }
  ]
}
```

Requirements:

- Support `links` and `edges`.
- Keep only `file_type == "code"` nodes.
- Ignore `semantically_similar_to` edges.
- Skip malformed nodes and edges.
- Skip edges whose source or target node was not kept.
- Never crash on unknown fields.

---

## 8. Configuration

Keel uses `.keel.yml`.

The file has two categories:

1. Human-defined repo model: layers, zones, packages, ignore paths.
2. Human-approved contracts generated or manually written.

Example:

```yaml
version: 1

project:
  name: demo-app

graph:
  provider: graphify
  path: graphify-out/graph.json

layers:
  UI:
    - src/components
    - src/pages
  API:
    - src/api
    - src/routes
  SERVICE:
    - src/services
  DATABASE:
    - src/db
    - src/repositories
  JOBS:
    - src/jobs
  TEST:
    - tests

zones:
  billing:
    - src/billing
    - src/services/billing
  auth:
    - src/auth
    - src/services/auth

ignore:
  - node_modules
  - dist
  - build
  - coverage
  - generated

approved_contracts:
  - id: ui_never_touches_database
    title: UI must not access database directly
    source: discovered
    status: approved
    evidence:
      discovered_at: "2026-06-01T00:00:00Z"
      ui_nodes: 42
      database_nodes: 9
      direct_edges_found: 0
    rule:
      forbid_edge:
        from_layer: UI
        to_layer: DATABASE
        relation: "*"
    repair:
      route_through_layer: SERVICE

  - id: stripe_only_from_billing
    title: Stripe package must stay inside billing
    source: discovered
    status: approved
    evidence:
      package: stripe
      importing_zones:
        - billing
    rule:
      external_package_scope:
        package: stripe
        allowed_zones:
          - billing
```

---

## 9. Data Models

Define these in `models.py`.

```python
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
```

Note: If Graphify does not expose external package imports distinctly, v1 can infer package-like
targets from graph edges only when Graphify includes enough target metadata. If not, external
package contracts become v2.

---

## 10. Contract Types

### 10.1 `forbid_edge`

Blocks a direct dependency between layers or zones.

```yaml
rule:
  forbid_edge:
    from_layer: UI
    to_layer: DATABASE
    relation: "*"
```

Violation:

```text
src/components/Dashboard.tsx imports src/db/users.ts, violating ui_never_touches_database.
```

### 10.2 `allow_only_path`

Requires dependencies to follow a layer route.

```yaml
rule:
  allow_only_path:
    route:
      - UI
      - SERVICE
      - DATABASE
```

This means UI may reach DATABASE only through SERVICE, not directly.

### 10.3 `external_package_scope`

Restricts an external package to specific layers or zones.

```yaml
rule:
  external_package_scope:
    package: stripe
    allowed_zones:
      - billing
```

### 10.4 `zone_ownership`

Restricts who can depend on a zone.

```yaml
rule:
  zone_ownership:
    zone: auth
    allowed_from_zones:
      - auth
    allowed_from_layers:
      - API
```

### 10.5 `no_cycles_between_layers`

Blocks cycles in the layer dependency graph.

```yaml
rule:
  no_cycles_between_layers:
    layers:
      - UI
      - API
      - SERVICE
      - DATABASE
```

---

## 11. Discovery Engine

The command:

```bash
keel discover .
```

Reads the current Graphify graph and proposes contracts.

It must not modify `.keel.yml` by default. It prints proposals or writes them to:

```text
keel-out/proposals.yml
```

Use:

```bash
keel discover . --write
```

to write proposals.

### 11.1 Discovery Principle

Only propose a contract when Keel has evidence that the codebase already follows the rule.

Bad:

```text
UI should probably never access DATABASE because that is clean architecture.
```

Good:

```text
There are 42 UI nodes and 9 DATABASE nodes. Existing UI nodes have 0 direct edges to DATABASE.
Existing DATABASE access flows through SERVICE in 8 observed paths.
```

### 11.2 Discovery Heuristics V1

Implement these first.

#### Heuristic A: Missing Direct Layer Edges

If there are many nodes in layer A and many nodes in layer B, but zero direct A -> B edges,
propose:

```yaml
forbid_edge:
  from_layer: A
  to_layer: B
```

Do not propose for tiny samples.

Minimum thresholds:

```text
from_layer_nodes >= 5
to_layer_nodes >= 3
direct_edges == 0
```

Avoid noisy proposals:

- Do not propose `TEST -> anything` by default.
- Do not propose involving `UNKNOWN` by default.
- Do not propose between layers configured as ignored.

#### Heuristic B: Existing Indirect Route

If A never calls C directly, but A -> B -> C paths exist, propose:

```yaml
allow_only_path:
  route: [A, B, C]
```

Minimum thresholds:

```text
path_count >= 3
direct_A_to_C_edges == 0
```

#### Heuristic C: Package Scope

If an external package appears only in one zone or layer, propose package scope.

Example:

```text
stripe imported by 7 files, all in billing zone
```

Propose:

```yaml
external_package_scope:
  package: stripe
  allowed_zones: [billing]
```

This heuristic is only enabled if Graphify provides package import information.

#### Heuristic D: Zone Ownership

If files in one zone are only depended on by a small approved set of zones/layers, propose
zone ownership.

Example:

```text
auth zone has 18 nodes. Incoming edges come only from auth and API.
```

Propose:

```yaml
zone_ownership:
  zone: auth
  allowed_from_zones: [auth]
  allowed_from_layers: [API]
```

#### Heuristic E: Layer DAG

If the layer dependency graph is acyclic, propose:

```yaml
no_cycles_between_layers:
  layers: [...]
```

This is useful because AI agents often create shortcuts that later create cycles.

### 11.3 Confidence

Confidence is deterministic.

High:

```text
strong sample size, zero violations, repeated alternate route observed
```

Medium:

```text
moderate sample size, zero violations, route evidence weak
```

Low:

```text
small sample size, use only as suggestion
```

Formula v1:

```text
high:
  from_nodes >= 10 and to_nodes >= 5 and direct_edges == 0

medium:
  from_nodes >= 5 and to_nodes >= 3 and direct_edges == 0

low:
  below medium threshold
```

Do not write low-confidence proposals unless `--include-low` is passed.

---

## 12. Approval Workflow

The command:

```bash
keel approve ui_never_touches_database .
```

Moves a proposal into `.keel.yml` under `approved_contracts`.

The command:

```bash
keel reject ui_never_touches_database .
```

Records the rejection in `keel-out/rejections.yml` so Keel does not keep proposing the same
contract.

### 12.1 Approval Requirements

When approving, preserve:

- contract id
- title
- rule
- evidence summary
- discovery timestamp
- repair settings

### 12.2 Manual Contracts

Users can write approved contracts manually in `.keel.yml`.

Keel should validate them exactly like discovered contracts.

---

## 13. Check Engine

The command:

```bash
keel check .
```

Runs approved contracts against the current Graphify graph.

Behavior:

- Load `.keel.yml`.
- Ensure/load Graphify graph.
- Assign layers and zones.
- Evaluate all approved contracts with `status: approved`.
- Print violations.
- Exit `1` if violations exist.
- Exit `0` if clean.

### 13.1 Changed Files

The command:

```bash
keel check . --changed src/components/Dashboard.tsx
```

For v1:

- rebuild or refresh Graphify graph
- evaluate all approved contracts
- filter violations involving changed files

Do not parse diffs in v1.

### 13.2 Baseline Mode

Some repos already have violations. Keel needs baseline support.

Command:

```bash
keel baseline .
```

Writes:

```text
keel-out/baseline.yml
```

`keel check` should report:

- new violations as blocking
- existing baseline violations as known debt

This prevents Keel from being unusable on older repos.

---

## 14. Repair Hints

Repair hints must be deterministic templates.

### 14.1 For `forbid_edge`

If repair config has `route_through_layer`:

```text
Move this dependency through SERVICE.
```

If Keel can find existing files in that layer connected to the target zone:

```text
Move this dependency through SERVICE. Existing candidates: src/services/userService.ts.
```

### 14.2 For `allow_only_path`

```text
Follow the approved route: UI -> SERVICE -> DATABASE.
```

### 14.3 For `external_package_scope`

```text
Keep package stripe inside billing. Add a billing service method instead of importing stripe here.
```

### 14.4 For `zone_ownership`

```text
Access auth through an approved API or auth service boundary.
```

---

## 15. Reports

### 15.1 Discover Report

Example:

```text
Keel discovered 3 candidate architecture contracts.

[high] ui_never_touches_database
UI must not access DATABASE directly
Evidence:
  UI nodes: 42
  DATABASE nodes: 9
  Direct UI -> DATABASE edges: 0
  Existing UI -> SERVICE -> DATABASE paths: 8
Rule:
  forbid_edge from UI to DATABASE
Repair:
  route through SERVICE

Approve:
  keel approve ui_never_touches_database .
```

### 15.2 Check Report

Example:

```text
Keel blocked 1 architecture regression.

1. src/components/Dashboard.tsx imports src/db/users.ts
   Contract: ui_never_touches_database
   Rule: UI must not access DATABASE directly
   Repair: Move this dependency through SERVICE. Existing candidates: src/services/userService.ts.
```

### 15.3 Clean Report

```text
Keel check passed. No architecture regressions found.
```

---

## 16. CLI Commands

Build these commands.

```text
keel init [PATH]
keel discover [PATH] [--write] [--include-low]
keel proposals [PATH]
keel approve CONTRACT_ID [PATH]
keel reject CONTRACT_ID [PATH]
keel check [PATH] [--changed FILE...]
keel baseline [PATH]
keel explain CONTRACT_ID [PATH]
keel export [PATH] [--format json]
```

### 16.1 `keel init`

Creates starter `.keel.yml`.

It should not overwrite an existing `.keel.yml` unless `--force`.

### 16.2 `keel discover`

Runs the invariant miner.

Default:

- print proposals
- no file changes

With `--write`:

- write `keel-out/proposals.yml`

### 16.3 `keel proposals`

Lists stored proposals.

### 16.4 `keel approve`

Adds one proposal to `.keel.yml`.

### 16.5 `keel reject`

Stores a rejection.

### 16.6 `keel check`

Runs approved contracts.

### 16.7 `keel baseline`

Stores existing violations as known debt.

### 16.8 `keel explain`

Shows:

- contract rule
- evidence
- examples
- repair strategy

### 16.9 `keel export`

Exports contracts, proposals, and check results as machine-readable JSON. External MCP
adapters, governance tools, or CI services should integrate with Keel through this boundary.

---

## 17. Agent Integration Boundary

MCP is outsourced. Keel must expose stable CLI and JSON outputs so an external adapter can wrap
it for Claude Code, Cursor, Codex, or other coding agents.

Keel should support these machine-readable commands:

```text
keel discover . --json
keel proposals . --json
keel check . --json
keel check . --changed FILE --json
keel explain CONTRACT_ID . --json
keel export . --format json
```

An external MCP adapter can expose these as tools:

```text
discover_contracts()
list_contracts()
explain_contract(contract_id)
check_change(files)
```

Approval should stay human-controlled through CLI or code review. External adapters should not
approve contracts by default.

---

## 18. Module Specifications

### 18.1 `config.py`

Loads and validates `.keel.yml`.

API:

```python
def load_config(repo_path: Path) -> Config:
    ...
def save_config(repo_path: Path, config: Config) -> None:
    ...
```

Validation:

- supported version
- layer prefixes are strings
- zone prefixes are strings
- contract ids are unique
- contract rules are known
- referenced layers/zones exist
- disabled contracts are ignored by check

### 18.2 `graphify_runner.py`

API:

```python
def ensure_graph(repo_path: Path, update: bool = False) -> Path:
    ...
```

Behavior:

- Return existing configured graph path if present.
- Run Graphify if needed.
- Raise clear error if Graphify is missing.

### 18.3 `graph.py`

API:

```python
def load_graph(graph_path: Path) -> KeelGraph:
    ...
```

Behavior:

- Parse Graphify JSON.
- Keep code nodes.
- Build connections.
- Optionally build external imports if Graphify provides them.

### 18.4 `layers.py`

API:

```python
def assign_layers_and_zones(graph: KeelGraph, config: Config) -> None:
    ...
```

Rules:

- Normalize path separators.
- Longest prefix wins for layer.
- A file can belong to multiple zones.
- Unknown layer is `UNKNOWN`.

### 18.5 `discover.py`

API:

```python
def discover_contracts(graph: KeelGraph, config: Config) -> list[ProposedContract]:
    ...
```

Implements the heuristics from section 11.

### 18.6 `contracts.py`

API:

```python
def load_approved_contracts(config: Config) -> list[ApprovedContract]:
    ...
def approve_contract(repo_path: Path, contract_id: str) -> ApprovedContract:
    ...
def reject_contract(repo_path: Path, contract_id: str) -> None:
    ...
```

### 18.7 `check.py`

API:

```python
def check_repo(repo_path: Path, changed_files: list[str] | None = None) -> list[Violation]:
    ...
def check_contract(graph: KeelGraph, contract: ApprovedContract) -> list[Violation]:
    ...
```

### 18.8 `repair.py`

API:

```python
def repair_hint(graph: KeelGraph, contract: ApprovedContract, violation: Violation) -> str | None:
    ...
```

### 18.9 `report.py`

API:

```python
def render_discover(proposals: list[ProposedContract]) -> str:
    ...
def render_check(violations: list[Violation]) -> str:
    ...
def render_explain(contract: ApprovedContract) -> str:
    ...
```

### 18.10 `memory.py`

Local store for later milestones.

Do not build first unless needed.

---

## 19. Build Milestones

### Milestone 1: Graph And Layer Foundation

Build:

- `models.py`
- `config.py`
- `graph.py`
- `layers.py`
- fixtures

Acceptance:

- sample graph loads without crashing
- only code nodes are kept
- `semantically_similar_to` is ignored
- layers and zones are assigned correctly
- tests pass

### Milestone 2: Discovery Engine

Build:

- `discover.py`
- `report.render_discover`
- `keel discover`

Acceptance:

- sample clean graph proposes `ui_never_touches_database`
- proposal includes confidence and evidence
- `keel discover` does not modify files by default
- `keel discover --write` writes `keel-out/proposals.yml`

### Milestone 3: Approval Workflow

Build:

- `contracts.py`
- `keel proposals`
- `keel approve`
- `keel reject`

Acceptance:

- approving a proposal writes it to `.keel.yml`
- rejecting a proposal prevents repeated noise
- invalid contracts fail validation with clear error

### Milestone 4: Check Engine

Build:

- `check.py`
- `repair.py`
- `report.render_check`
- `keel check`

Acceptance:

- clean graph passes
- regressed graph fails
- failure exits code `1`
- violation names contract id and title
- violation includes repair hint

### Milestone 5: Baseline Support

Build:

- `keel baseline`
- baseline filtering in `keel check`

Acceptance:

- existing violations can be baselined
- new violations still fail
- baseline report distinguishes known debt from new regressions

### Milestone 6: Adapter Export API

Build:

- `--json` output for core commands
- `keel export`
- stable JSON schemas for proposals, contracts, violations, and reports

Acceptance:

- external tools can consume Keel without importing Python modules
- `keel check --json` returns structured violations
- `keel discover --json` returns structured proposals
- `keel export` returns config, approved contracts, and latest proposals

### Milestone 7: Memory And Governance Export

Build:

- SQLite event store
- event export JSONL
- optional webhook or file export for governance tools

Acceptance:

- checks are recorded
- approvals/rejections are recorded
- event log can be replayed

---

## 20. Test Fixture Design

### 20.1 Clean Graph

`sample_clean_graph.json`:

- 8 UI nodes
- 4 SERVICE nodes
- 3 DATABASE nodes
- UI -> SERVICE edges
- SERVICE -> DATABASE edges
- no UI -> DATABASE edges

Expected:

- `keel discover` proposes `UI must not access DATABASE directly`
- `keel check` passes after approval

### 20.2 Regressed Graph

`sample_regressed_graph.json`:

Same as clean graph, plus:

```text
src/components/Dashboard.tsx -> src/db/users.ts
```

Expected:

- approved contract fails
- violation points to `Dashboard.tsx`
- repair says to route through SERVICE

### 20.3 Semantically Similar Edge

Include:

```json
{
  "source": "src/components/Dashboard.tsx::Dashboard",
  "target": "src/db/users.ts::getUserById",
  "relation": "semantically_similar_to"
}
```

Expected:

- no violation from this edge

---

## 21. README Positioning

README headline:

```text
Keel finds the unwritten rules of your codebase and makes them executable.
```

Subheadline:

```text
Architecture regression tests for AI-generated code, powered by Graphify.
```

README sections:

1. Problem
2. How Keel works
3. Graphify + Keel boundary
4. Quickstart
5. Discover contracts
6. Approve contracts
7. Check regressions
8. Agent adapter integration
9. CI usage
10. Limitations

Limitations:

- Keel depends on Graphify's graph quality.
- Keel proposes likely invariants, not universal truths.
- Human approval is required before enforcement.
- Layer and zone assignment are folder-based in v1.
- Keel is not a general code quality reviewer.
- Keel does not replace tests.

---

## 22. Demo

Build this demo:

```text
demo-app/
  src/components/Dashboard.tsx
  src/services/userService.ts
  src/db/users.ts
  tests/userService.test.ts
  .keel.yml
```

Demo script:

1. Run `graphify`.
2. Run `keel discover`.
3. Keel proposes:

```text
UI must not access DATABASE directly
```

4. Run `keel approve ui_never_touches_database`.
5. Ask an AI agent to add user profile loading.
6. Agent imports `src/db/users.ts` inside `Dashboard.tsx`.
7. Run `keel check`.
8. Keel blocks the architecture regression.
9. Agent repairs by adding `src/services/userService.ts`.
10. Run `keel check`.
11. Keel passes.

This demo is the product.

---

## 23. Future Ideas

Only after the core works:

- ADR-to-contract compiler
- route inference improvements
- package import contracts
- database table ownership contracts
- framework-specific presets
- GitHub Actions
- PR comment bot
- HTML architecture regression report
- GovForge-style audit export
- multi-repo invariants
- optional LLM explanation layer, never LLM enforcement

---

## 24. Final Definition

Keel is successful when a user can run:

```bash
keel discover .
keel approve ui_never_touches_database .
keel check .
```

and feel:

```text
The architecture my repo already follows is now protected from AI drift.
```
