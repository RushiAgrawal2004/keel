---
keel_contract:
  id: ui_never_touches_database
  title: UI must not access DATABASE directly
  rule:
    forbid_edge:
      from_layer: UI
      to_layer: DATABASE
      relation: "*"
  repair:
    route_through_layer: SERVICE
---

# ADR 0001: UI Database Boundary

UI code should not depend directly on database modules. Database access should move through a service boundary so UI changes do not couple presentation code to persistence details.

Keel can compile the frontmatter in this ADR into a reviewable contract artifact:

```bash
keel adr-compile . --write
```

