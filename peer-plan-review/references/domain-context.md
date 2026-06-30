# Domain-context block — authoring guide

Loaded when you have decided a review needs host-specific criteria (the inclusion test lives in
`SKILL.md` § Domain context). This file is *how* to author the block once you've decided to add one.

## Why it's gated

Baseline testing confirmed an asymmetry: a strong reviewer flagged idiomatic SwiftUI violations
unaided but missed bespoke project rules (e.g. "writes must go through the audit store", "every
model must be registered or it loses data on migration") entirely. So a block earns its prompt
weight only for project-specific invariants absent from any public standard, framework guide, or
common convention — a custom audit-store contract, a private migration invariant. General idioms
are pure overhead.

## Author it as criteria, not prescriptions

State the standard the plan must meet; never restate the solution the plan already chose. Hard
rule while writing it:

> Do not reference the specific files, classes, or architectural choices made in the plan.
> Output only the abstract rules the plan must satisfy — 3–6 bullets, one checkable rule each.

## Placement

Between the numbered plan and the output template, in this shape:

```
## Domain context (review criteria — challenge these if any are wrong)
- <checkable rule 1>
- <checkable rule 2>
```

## Two-pass output

When a block is present, the reviewer uses the two-pass output variant in
[`output-format.md`](output-format.md): an independent Pass A that must not assume the criteria
are right, then a Pass B that checks the plan against the criteria **and challenges the criteria
themselves**. That preserves the independent second opinion — the reviewer can reject a biased or
incomplete block instead of rubber-stamping the host's framing.
