---
name: doc-standardization
description: >-
  Standardize Markdown documentation trees by discovering the project-local docs
  contract, fixing naming drift, broken internal links, stale README indexes,
  orphaned docs, H1 drift, and declared exceptions. Use when renaming docs,
  reorganizing docs folders, auditing docs before release, fixing Markdown
  links, updating docs indexes, handling ADRs or dated records, or aligning a
  repo's documentation with its own documented taxonomy.
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
---

# Documentation Standardization

Keep docs trees coherent without forcing every repo into one folder layout.
Discover the local contract from `docs/README.md` or the nearest index, then
enforce link integrity, index accuracy, naming hygiene, and documented
exceptions.

## Workflow

### 1. Discover the local contract

Read the nearest `README.md` before renaming. Treat it as the source of truth
for project areas, special bundles, and exceptions. If no contract exists, use
the default grammar in [`references/conventions.md`](references/conventions.md).

Look for:
- curated project areas such as `product/`, `qa/`, `architecture/`, or `adr/`
- special cases such as vendor docs, Obsidian vaults, archives, generated docs
- required index files and dated record conventions

Carry what you discover into the audit as flags — the script enforces a
repo-agnostic default, so a declared bundle it does not recognize by default
(anything outside `vendor`/`archive`/`_archive`) or a custom type/status vocab
must be passed explicitly (see step 2). You read the contract; the script
enforces the parts you hand it.

### 2. Audit current state

Run the bundled audit script from the target repo root, passing any
contract details you discovered in step 1:

```bash
bash <skill-path>/scripts/check-doc-naming.sh docs \
  --bundle-glob '*/legal/*' \    # a README-declared preserved bundle
  --types 'rfc' \                # a project-local type token
  --allow NOTICE.md              # an extra top-level file
```

Flags (repeatable where noted, run `--help` for the full list):
- `--bundle-glob GLOB` — exempt a declared bundle from filename hygiene (links
  inside are still validated). Built-in defaults: `vendor`, `archive`,
  `_archive`.
- `--types 'a|b'` / `--states 'a|b'` — extend the recognized vocab with literal
  ERE alternation fragments appended to the defaults.
- `--allow NAME` — allowlist an extra basename.

Exit codes: `0` clean, `1` blocking violations found, `2` invocation error.
Output classes map to fixes in
[`references/error-taxonomy.md`](references/error-taxonomy.md).

### 3. Choose the target path

Prefer the repo's documented taxonomy over a universal directory tree. For
ordinary curated docs, use:

```text
<topic>-<type>-<status>.md
```

For dated records, use:

```text
<topic>-<type>-YYYY-MM-DD.md
```

ADRs may keep `NNNN-topic.md`. Declared tool, vendor, and archive bundles may
preserve their native filenames when the nearest `README.md` explains why.

### 4. Rename and repair references

Find references before moving a file:

```bash
grep -rn "old-filename.md" .
git mv docs/old-name.md docs/new-name.md
```

Then update:
- every reference found by the search
- the H1 in the renamed file when it no longer matches the topic
- every affected `README.md` index entry
- any local exception notes if the file belongs to a declared bundle

### 5. Re-audit and pre-flight

Re-run the audit script. Before handoff, verify:
- final paths match the discovered contract or documented exceptions
- internal Markdown links are valid
- `README.md` indexes point at existing files
- remaining `ORPHAN`, `H1-DRIFT`, or advisory `NAMING` lines are intentional
- no blocking `[FAIL]` class remains

### 6. Wire optional project validators

Use project-local validators for semantic checks that the base skill cannot
know, such as code-to-doc identifier alignment or product-specific status
rules:

```bash
bash <skill-path>/scripts/check-doc-naming.sh docs || exit 1
./scripts/validate_naming_consistency.sh
```

## Common Mistakes

1. **Flattening useful project taxonomy** - keep local areas when the index
   explains their purpose.
2. **Missed references** - search for the old basename before `git mv`.
3. **Undeclared exceptions** - preserve vendor or tool-native filenames only
   when the nearest index explains the exception.
4. **Stale indexes** - update `README.md` entries in the same change.
5. **Treating advisories as clean** - triage each `ORPHAN`, `H1-DRIFT`, and
   advisory `NAMING` line before handoff.

## Examples

**Rename a project-local spec:**

```bash
grep -rn "transition-modes-spec.md" .
git mv docs/product/transition-modes-spec.md docs/product/transition-modes-spec-implemented.md
# Update H1 and every reference found by grep
bash <skill-path>/scripts/check-doc-naming.sh docs
```

**Preserve a declared vault bundle:**

```bash
# docs/architecture/code-flow/README.md documents that Obsidian filenames are preserved.
bash <skill-path>/scripts/check-doc-naming.sh docs --bundle-glob '*/code-flow/*'
# Native filenames inside the declared bundle are accepted; links are still validated.
```

## Related Skills

- [`bash-macos`](../bash-macos/SKILL.md) - consult before changing shell
  recipes or audit scripts.

## References

- [`references/conventions.md`](references/conventions.md) - default naming
  grammar, dated records, ADRs, project taxonomy, and exception rules
- [`references/error-taxonomy.md`](references/error-taxonomy.md) - output class
  to canonical fix mapping
- [`references/regex-recipes.md`](references/regex-recipes.md) - portable shell
  recipes and expected outputs
- [`scripts/check-doc-naming.sh`](scripts/check-doc-naming.sh) - read-only audit
  script; exit `0`/`1`/`2`
