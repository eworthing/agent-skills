# Conventions Reference

Use this default contract when a project has no stronger local convention.
When `docs/README.md` or a nearer index defines a project taxonomy, preserve
that taxonomy and enforce the file-level rules inside it.

## Project-local taxonomy

Directories carry project meaning. A software repo may reasonably have
`product/`, `qa/`, `adr/`, `architecture/`, `superpowers/`, or other local
areas. Do not replace those with a universal folder tree when the index explains
their purpose.

Every curated docs area should have either:
- a `README.md` that explains what belongs there, or
- an entry in the parent `README.md`.

## Default filename grammar

For curated docs that opt into the standard:

```text
<topic>-<type>-<status>.md
```

| Component | Values | Example |
|---|---|---|
| topic | short lowercase slug | `transition-modes` |
| type | `spec`, `guide`, `ref`, `research`, `audit`, `plan`, `decision` | `spec` |
| status | `draft`, `proposed`, `active`, `implemented`, `deprecated` | `implemented` |

Examples:
- `transition-modes-spec-implemented.md`
- `developer-vm-setup-guide-active.md`
- `accessibility-identifiers-ref-active.md`
- `playlist-bulk-add-plan-proposed.md`

## Dated records

Use dates when the date is part of the document identity, especially audits,
handoffs, incident reviews, and point-in-time research:

```text
<topic>-<type>-YYYY-MM-DD.md
```

Examples:
- `test-suite-audit-2026-06-14.md`
- `apple-music-handoff-2026-06-17.md`
- `sim-runtime-audit-2026-06-15.md`

Use one date convention per area. Prefer `YYYY-MM-DD`; use `YYYY-MM` only when
the area documents monthly records and the README says so.

## ADRs

Architecture Decision Records may keep numeric ordering:

```text
NNNN-topic.md
```

Example: `0001-reject-transport-parity-tests.md`.

The ADR body should carry decision metadata such as status, date, deciders, and
context.

## Exceptions

Some docs should preserve native filenames:

- **Vendor docs** - preserve upstream names so updates diff cleanly.
- **Tool bundles** - preserve names needed by tools such as Obsidian or export
  pipelines.
- **Archives** - preserve names when historical references matter.
- **Top-level files** - `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`,
  `LICENSE.md`, `CODEOWNERS`, and `index.md` are pre-allowlisted.

Document each exception in the nearest `README.md`. The audit script exempts the
generic bundle paths `vendor`, `archive`, and `_archive` from filename hygiene
by default; any other declared bundle is passed at audit time via
`--bundle-glob '<pattern>'`, and project-local type/status vocab via
`--types` / `--states` (see the SKILL.md audit step). Links inside every exempt
bundle are still validated.

## Code-to-document alignment

Code identifier alignment is project-specific. If a repo needs docs to match
typed enum cases, test scenario names, or product identifiers, add a local
validator and run it alongside `scripts/check-doc-naming.sh`.
