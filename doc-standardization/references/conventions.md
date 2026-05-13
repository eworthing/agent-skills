# Conventions Reference

Lookup tables and the canonical `docs/` tree layout. SKILL.md links here
instead of inlining these so the workflow body stays small.

## Naming convention

`[domain]-[feature]-[type]-[status].md`

| Component | Values | Example |
|-----------|--------|---------|
| domain | ui, data, core, test, ai, build, infra, security | `ui-` |
| feature | specific feature slug | `button-styles-` |
| type | spec, guide, research, reference | `-spec-` |
| status | draft, proposed, active, implemented, deprecated, baseline-audit, research | `-implemented` |

Examples:
- `ui-pattern-button-styles-spec-implemented.md`
- `data-persistence-swiftdata-migrations-spec-implemented.md`
- `test-ui-automation-guide.md`

Allowlisted basenames (do not follow convention): `README.md`,
`CHANGELOG.md`, `CONTRIBUTING.md`, `LICENSE.md`, `CODEOWNERS`, `index.md`.

## Status suffixes

| Status | Use Case | Example |
|--------|----------|---------|
| `-draft` | Work in progress | `ui-overlay-spec-draft.md` |
| `-proposed` | Awaiting approval | `ui-overlay-spec-proposed.md` |
| `-active` | Approved, implementation ongoing | `ui-overlay-spec-active.md` |
| `-implemented` | Complete and in production | `ui-overlay-spec-implemented.md` |
| `-deprecated` | Superseded, kept for reference | `ui-overlay-spec-deprecated.md` |
| `-baseline-audit` | Audit/snapshot document | `architecture-baseline-audit.md` |
| `-research` | Discovery/investigation | `ui-focus-research.md` |

## Directory tree

```
docs/
  archive/          # Superseded documents (move here instead of delete)
    README.md       # Index explaining why each doc was archived
  specs/            # Formal specifications
    README.md       # Index of all specs
    *.md            # [domain]-[feature]-spec-[status].md
  patterns/         # UI patterns and best practices
  research/         # Discovery and investigation docs
  testing/          # Test guides and strategies
  features/         # Feature-specific documentation
    {feature}/      # One subdirectory per major feature
      README.md     # Feature overview and links
  reference/        # Deep reference material
  vendor/           # Vendor-supplied docs (filenames preserved upstream)
```

## Code ↔ Documentation alignment

When docs reference code identifiers (enums, types, scenarios), names must
align so future readers can follow a doc → code → test trail without
guessing.

| Code identifier | Doc reference |
|-----------------|---------------|
| `ScreenIdentifier.searchScreen` | "Search screen", link to `SearchView.swift` |
| `SnapshotScenario.homeScreenDefault` | "HomeScreen_Default scenario" |

Maintain a project-specific consistency check that cross-references:
- Typed identifier enum cases (e.g. `ScreenIdentifier`, `AccessibilityID`)
- Identifier strings referenced from testing-contract docs
- Snapshot/visual-audit scenario lists used by test runners

Wire alongside [`scripts/check-doc-naming.sh`](../scripts/check-doc-naming.sh)
in the pre-commit gate or CI smoke step. Mismatches should fail the build,
not warn.

## When to break the convention

Some files legitimately diverge:

- **Vendor-supplied docs** — preserve upstream filenames so updates diff
  cleanly. Place under `docs/vendor/<vendor>/` and note in the parent
  `README.md`.
- **Legacy specs** — when renaming would break external bookmarks or
  commit-message references. Move to `docs/archive/` with a rationale in
  `docs/archive/README.md`.
- **Top-level files** — `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`,
  `LICENSE.md`, `CODEOWNERS`, `index.md` are pre-allowlisted in the audit
  script.

For each exception leave a note in the nearest `README.md` so the next
contributor knows it is intentional.

## Hard limits

- Maximum 600 lines per documentation file
- GitHub-flavored Markdown
- Paths under 100 characters
- No spaces in filenames — use hyphens
- Lowercase only (excepting allowlisted bases above)
