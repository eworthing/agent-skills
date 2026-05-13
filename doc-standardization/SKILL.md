---
name: doc-standardization
author: eworthing
description: >-
  Standardize documentation naming, organization, and cross-references in
  Markdown-based project docs. Enforces a consistent
  `[domain]-[feature]-[type]-[status].md` filename pattern, valid internal
  links, ordered index files, and code-to-doc identifier alignment. Use when
  renaming docs, standardizing specs, fixing broken markdown links, organizing
  documentation, moving files between doc directories, consolidating or
  splitting docs, or auditing a docs tree before a release.
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
---

# Documentation Standardization

Keep docs trees consistent as they grow: stable filename convention, valid
internal links, ordered indexes, code↔doc identifier alignment. Catches
naming drift, broken links, orphans, and index drift that accumulate in
long-lived `docs/` trees.

## When to Use

Use when:
- Adding new doc files
- Renaming or reorganizing existing docs
- User says "standardize docs", "fix doc links", "organize specs"
- Moving files between doc directories
- Consolidating or splitting docs
- Auditing a docs tree before release

Do NOT use when:
- Editing content within a single file (no structural changes)
- Working on non-doc files
- Quick README edits with no cross-references

## Workflow

### 1. Audit current state

Ships with a one-shot drift verifier:

```bash
bash <skill-path>/scripts/check-doc-naming.sh docs
# Clean: "== summary: CLEAN ...", exit 0
# Fail:  per-class FAIL lines, exit 1
```

Underlying patterns live in
[`references/regex-recipes.md`](references/regex-recipes.md) — one recipe
per error class with expected-clean and expected-failure outputs.

### 2. Pick the new name

Use the convention `[domain]-[feature]-[type]-[status].md`. Full lookup
tables (domain values, status suffixes, directory layout) in
[`references/conventions.md`](references/conventions.md).

### 3. Rename

```bash
grep -rn "old-filename.md" .             # find references
git mv docs/old-name.md docs/new-name.md # rename (reversible)
```

Then update:
- All references found in step 1 (Edit each file)
- The H1 inside the renamed file
- Any `README.md` index entries

### 4. Re-audit

```bash
bash scripts/check-doc-naming.sh docs
```

Exit codes: `0` clean, `1` violations found, `2` invocation error.

Each output class — `BROKEN`, `ORPHAN`, `INDEX-DRIFT`, `CASE`, `NAMING` —
maps to a canonical fix in
[`references/error-taxonomy.md`](references/error-taxonomy.md).

### 5. Wire optional project validators

```bash
# Pre-commit gate
bash scripts/check-doc-naming.sh docs || exit 1
./scripts/validate_naming_consistency.sh   # project-specific cross-checks
```

Project-specific validators typically cross-check doc filenames against
code identifiers and test scenarios — see
[`references/conventions.md`](references/conventions.md#code--documentation-alignment).

## Common Mistakes

1. **Missed reference updates** — always `grep` the old filename first
2. **H1 / filename drift** — H1 should mention the primary slug token
3. **Wrong status suffix** — `-implemented` for done, `-draft` for WIP
4. **Forgotten index updates** — update `README.md`, re-run audit
5. **Mixed case** — lowercase + hyphens only (allowlisted bases excepted)

For legitimate exceptions (vendor docs, legacy specs, top-level files),
see [`references/conventions.md`](references/conventions.md#when-to-break-the-convention).

## Examples

**Rename a spec:**

```bash
grep -rn "toolbar-spec.md" .
git mv docs/specs/toolbar-spec.md docs/specs/ui-toolbar-unification-spec-implemented.md
# Edit H1 in the renamed file: "# UI Toolbar Unification Spec"
# Edit every file from the grep output
bash scripts/check-doc-naming.sh docs   # expect: CLEAN
```

**Organize research docs:**

```bash
mkdir -p docs/research
git mv docs/toolbar-research.md docs/research/ui-toolbar-architecture-research.md
git mv docs/focus-research.md   docs/research/ui-focus-management-research.md
bash scripts/check-doc-naming.sh docs
```

## Related Skills

- [`bash-macos`](../bash-macos/SKILL.md) — Portability rules the audit script
  follows. Consult before adding shell recipes.
- [`swift-file-splitting`](../swift-file-splitting/SKILL.md) — Analogous
  max-file-size pattern for code; the 600-line doc cap mirrors its
  `file_length` enforcement.

## References

- Project `AGENTS.md` / `CLAUDE.md` — repo-pinned renaming rules
- [`references/regex-recipes.md`](references/regex-recipes.md) — hardened
  bash one-liners per error class with expected outputs
- [`references/error-taxonomy.md`](references/error-taxonomy.md) — error
  class → detector → canonical fix
- [`references/conventions.md`](references/conventions.md) — naming
  components, status suffixes, directory tree, code↔doc alignment,
  exceptions
- [`scripts/check-doc-naming.sh`](scripts/check-doc-naming.sh) — one-shot
  audit runner; exit 0/1/2
- CommonMark Spec — <https://spec.commonmark.org/> — link syntax,
  reference-style links, parser semantics
- GitHub Flavored Markdown Spec — <https://github.github.com/gfm/> —
  autolinks, table syntax, GitHub extensions
