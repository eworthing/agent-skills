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

## Purpose

Ensures consistent documentation naming conventions, file organization, and
valid cross-references across a project's Markdown docs. Addresses recurring
patterns of naming drift, broken links, and organizational inconsistency that
accumulate over time as a doc tree grows.

## When to Use This Skill

Use this skill when:
- Adding new documentation files
- Renaming or reorganizing existing docs
- User says "standardize docs", "fix doc links", "organize specs"
- Moving files between documentation directories
- Consolidating or splitting documentation

Do NOT use this skill when:
- Editing content within a single file (no structural changes)
- Working on non-documentation files
- Quick README updates with no cross-references

## Workflow

### Step 1: Understand Naming Convention

Documentation follows `[domain]-[feature]-[type]-[status].md`:

| Component | Values | Examples |
|-----------|--------|----------|
| domain | ui, data, core, test, ai, etc. | `ui-` |
| feature | specific feature name | `button-styles-` |
| type | spec, guide, research, reference | `-spec-` |
| status | draft, proposed, active, implemented, deprecated, baseline-audit, research | `-implemented` |

**Examples:**
- `ui-pattern-button-styles-spec-implemented.md`
- `data-persistence-swiftdata-migrations-spec-implemented.md`
- `test-ui-automation-guide.md`

### Step 2: Audit Current State

```bash
# Find all markdown files in docs/
find docs -name "*.md" -type f | sort

# Check for naming violations (missing hyphens, wrong suffixes)
find docs -name "*.md" | grep -v -E "[a-z]+-[a-z]+-" | head -20

# Find broken internal links
grep -rn "\]\(.*\.md\)" docs/ | grep -v "http"
```

### Step 3: Rename Files

When renaming:

1. **Identify the new name** using the convention
2. **Search for all references** to the old filename:
   ```bash
   grep -rn "old-filename.md" .
   ```
3. **Rename the file** using `git mv`:
   ```bash
   git mv docs/old-name.md docs/new-name.md
   ```
4. **Update all references** in other files
5. **Update the H1 title** inside the file to match

### Step 4: Fix Cross-References

```bash
# Find all internal markdown links
grep -rn "\]\(\.\./\|\./" docs/ --include="*.md"

# Validate links exist
for link in $(grep -roh "\]\([^)]*\.md\)" docs/ | sed 's/\](\(.*\))/\1/'); do
  if [[ ! -f "docs/$link" && ! -f "$link" ]]; then
    echo "BROKEN: $link"
  fi
done
```

### Step 5: Update Index Files

Update `docs/specs/README.md` or relevant index with new file paths:
- Alphabetize entries
- Use consistent link formatting: `- [Title](filename.md)`

### Step 6: Validation

```bash
# Verify no broken links remain
grep -rn "\.md)" docs/ | while read line; do
  file=$(echo "$line" | grep -o '[^(]*\.md' | head -1)
  if [[ -n "$file" && ! -f "$file" ]]; then
    echo "BROKEN: $line"
  fi
done

# Run markdownlint
npx markdownlint-cli2 "docs/**/*.md"
```

### Step 7: Run Project-Specific Validation (Optional)

If the project ships a naming-consistency validator (often a shell script that
cross-checks doc filenames against code identifiers and test scenarios), run
it before committing:

```bash
# Generic invocation — adjust path per project
./scripts/validate_naming_consistency.sh
```

Wire such a validator into the project's pre-commit gate or CI smoke step so
naming drift fails fast.

## Common Mistakes to Avoid

Based on historical patterns across long-lived doc trees:

1. **Missing reference updates** — Always `grep` for the old filename before renaming
2. **Inconsistent H1 titles** — The H1 inside the file should match the friendly name
3. **Wrong status suffix** — Use `-implemented` for done specs, `-draft` for WIP
4. **Forgetting index updates** — Always update `README.md` index files
5. **Case sensitivity** — Use lowercase with hyphens, never camelCase

## Examples

### Example 1: Renaming a Spec File

**Before:**
```
docs/specs/toolbar-spec.md
```

**After:**
```bash
# 1. Find references
grep -rn "toolbar-spec.md" .

# 2. Rename
git mv docs/specs/toolbar-spec.md docs/specs/ui-toolbar-unification-spec-implemented.md

# 3. Update internal H1
# Change: # Toolbar Spec
# To:     # UI Toolbar Unification Spec

# 4. Update all references found in step 1
```

### Example 2: Organizing Research Documents

**Before:**
```
docs/toolbar-research.md
docs/focus-research.md
```

**After:**
```bash
mkdir -p docs/research
git mv docs/toolbar-research.md docs/research/ui-toolbar-architecture-research.md
git mv docs/focus-research.md docs/research/ui-focus-management-research.md
```

## Directory Structure Reference

```
docs/
  archive/         # Superseded documents (move here instead of delete)
    README.md      # Index explaining why each doc was archived
  specs/           # Formal specifications
    README.md      # Index of all specs
    *.md           # [domain]-[feature]-spec-[status].md
  patterns/        # UI patterns and best practices
  research/        # Discovery and investigation docs
  testing/         # Test guides and strategies
  features/        # Feature-specific documentation
    {feature}/     # One subdirectory per major feature
      README.md    # Feature overview and links
  reference/       # Deep reference material
```

## Status Suffix Reference

| Status | Use Case | Example |
|--------|----------|---------|
| `-draft` | Work in progress | `ui-overlay-spec-draft.md` |
| `-proposed` | Awaiting approval | `ui-overlay-spec-proposed.md` |
| `-active` | Approved, implementation ongoing | `ui-overlay-spec-active.md` |
| `-implemented` | Complete and in production | `ui-overlay-spec-implemented.md` |
| `-deprecated` | Superseded, kept for reference | `ui-overlay-spec-deprecated.md` |
| `-baseline-audit` | Audit/snapshot document | `architecture-baseline-audit.md` |
| `-research` | Discovery/investigation | `ui-focus-research.md` |

## Code-Documentation Alignment

When documentation references code identifiers (enums, types, scenarios),
names must align so future readers can follow a doc → code → test trail
without guessing.

| Code | Documentation Reference |
|------|-------------------------|
| `ScreenIdentifier.searchScreen` | "Search screen", link to `SearchView.swift` |
| `SnapshotScenario.homeScreenDefault` | "HomeScreen_Default scenario" |

**Validation:** Maintain a project-specific consistency check (typically a
shell script under `scripts/`) that cross-references:

- Typed identifier enum cases (e.g. `ScreenIdentifier`, `AccessibilityID`)
- Identifier strings referenced from testing-contract docs
- Snapshot/visual-audit scenario lists used by test runners

Wire the check into the pre-commit gate or CI smoke step. Mismatches between
the three sources should fail the build rather than warn.

## References

- Project-level `AGENTS.md` or `CLAUDE.md` — typically pins renaming and
  documentation rules per repository
- Project-specific `scripts/validate_naming_consistency.sh` (if present) —
  catches naming drift between docs, code, and tests

## Constraints

- Maximum 600 lines per documentation file
- Use GitHub-flavored Markdown
- Keep file paths under 100 characters
- No spaces in filenames—use hyphens
