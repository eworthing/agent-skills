# Regex Recipes: Doc Audit Patterns

Portable shell recipes behind `doc-standardization`. The bundled
[`scripts/check-doc-naming.sh`](../scripts/check-doc-naming.sh) runs these as a
single audit.

All recipes target Bash 3.2+ plus BSD or GNU userland.

## 1. List markdown files

```bash
find docs -type f -name "*.md" | LC_ALL=C sort
```

- **Clean output:** alphabetized list of `*.md` paths.
- **Invocation failure:** missing `docs/` directory.

## 2. Detect universal hygiene failures

Curated filenames should be lowercase kebab-case. Allowlisted top-level names,
ADRs, dated records, and declared bundles are handled separately. Project-local
contracts extend this at audit time via `check-doc-naming.sh` flags —
`--bundle-glob` (exempt a declared bundle), `--allow` (extra basename), and
`--types` / `--states` (extend the grammar vocab).

```bash
base="${f##*/}"
if ! printf '%s' "$base" | grep -Eq '^[a-z0-9]+(-[a-z0-9]+)*\.md$'; then
  printf 'CASE: %s\n' "$f"
fi
```

- **Clean output:** no lines.
- **Failure output:** `CASE: docs/product/Transition Modes.md`.

## 3. Recognize default grammar

```bash
printf '%s' "$base" | grep -Eq '^[a-z0-9]+(-[a-z0-9]+)*-(spec|guide|ref|research|audit|plan|decision)-(draft|proposed|active|implemented|deprecated)\.md$'
```

- **Pass:** `transition-modes-spec-implemented.md`.
- **Blocking `NAMING`:** recognized type with invalid status, such as
  `transition-modes-spec-shelved.md`.
- **Advisory `NAMING`:** lower-kebab project-local names such as
  `test-plan.md`.

## 4. Recognize dated records

```bash
printf '%s' "$base" | grep -Eq '^[a-z0-9]+(-[a-z0-9]+)*-(spec|guide|ref|research|audit|plan|decision)-[0-9]{4}-[0-9]{2}-[0-9]{2}\.md$'
```

- **Pass:** `test-suite-audit-2026-06-14.md`.
- **Use when:** the date is part of document identity.

## 5. Recognize ADRs

```bash
case "$f" in
  */adr/[0-9][0-9][0-9][0-9]-*.md) printf 'ADR\n' ;;
esac
```

- **Pass:** `docs/adr/0001-reject-transport-parity-tests.md`.
- **Note:** ADR status belongs in the body, not the basename.

## 6. Validate links exist

Walk every Markdown link, skip external URLs, `mailto:`, and anchors-only,
URL-decode `%20`, and resolve relative targets against the source file's
directory.

```bash
grep -En '\]\([^)]*\.md(#[^)]*)?\)' "$f"
```

- **Clean output:** `[OK] links: 0 broken (N checked)`.
- **Failure output:** `BROKEN: docs/specs/foo.md:42 -> ../missing.md`.

## 7. Find orphan markdown files

A file is orphaned when no other Markdown file references its basename.

```bash
grep -rEl "\\]\\([^)]*${base}([#)])" docs --include="*.md"
```

- **Clean output:** no lines.
- **Advisory output:** `ORPHAN: docs/research/dropped-feature.md`.
- **Known false positives:** files referenced from source code, release notes,
  or external systems.

## 8. Find index drift

Index files sometimes reference deleted or renamed targets.

```bash
find docs -name "README.md" -type f -print
```

- **Clean output:** no lines.
- **Failure output:** `INDEX-DRIFT: docs/README.md references missing plans/old-plan.md`.

## 9. Find H1 drift

Compare the H1 against the first meaningful topic token in the filename.

```bash
h1=$(grep -m1 -E '^# ' "$f" | sed 's/^# //')
```

- **Clean output:** no lines.
- **Advisory output:** `H1-DRIFT: docs/product/foo-spec-active.md -> H1 "Bar" missing slug token "foo"`.
