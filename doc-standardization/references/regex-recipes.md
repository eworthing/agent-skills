# Regex Recipes: Doc Audit Patterns

Hardened shell recipes for `doc-standardization`. Each recipe lists the
**command**, **expected output when clean**, **expected output on failure**,
and **known false positives**.

All commands target portable Bash 3.2+ / BSD or GNU userland. See the
`bash-macos` sibling skill for cross-platform shell rules.

> **Run from the repo root.** Recipes that walk `docs/` assume the working
> directory is the project root so relative links resolve correctly.

---

## 1. List markdown files

```bash
find docs -type f -name "*.md" | sort
```

- **Clean output:** alphabetized list of all `*.md` paths.
- **Failure mode:** missing `docs/` directory → `find: docs: No such file or directory`.

---

## 2. Detect naming-convention violations

The convention is `[domain]-[feature]-[type]-[status].md`. A loose audit
flags filenames missing at least two hyphens or containing uppercase.

```bash
find docs -type f -name "*.md" -print | while IFS= read -r f; do
  base="${f##*/}"
  case "$base" in
    README.md|CHANGELOG.md|CONTRIBUTING.md|LICENSE.md) continue ;;
  esac
  # Must contain >=2 hyphens, lowercase only
  if ! printf '%s' "$base" | grep -Eq '^[a-z0-9]+(-[a-z0-9]+){2,}\.md$'; then
    printf 'NAMING: %s\n' "$f"
  fi
done
```

- **Clean output:** (no lines printed)
- **Failure output:** `NAMING: docs/specs/Toolbar.md`
- **Known false positives:** Top-level `README.md` / `CHANGELOG.md` /
  `CONTRIBUTING.md` / `LICENSE.md` are pre-skipped by the `case` block.
  Add other allowlisted basenames there.

---

## 3. Find internal markdown links

Lists every `*.md` link expression so you can audit them.

```bash
grep -rEn '\]\(([^)]*\.md)(#[^)]*)?\)' docs/ --include="*.md"
```

- **Clean output:** one match per link (file:line:match).
- **Note:** captures both relative (`./foo.md`, `../bar/baz.md`) and
  bare (`baz.md`) forms. Anchors (`#section`) are matched and ignored
  by the validator below.

---

## 4. Validate links exist (hardened)

Walks every link, skips external URLs / mailto / anchors-only, URL-decodes
`%20`, and resolves relative paths against the **source file's directory**
(not just `docs/` root). Reports `BROKEN:` per failure and `OK: 0 broken
links` when clean.

```bash
broken=0
total=0
while IFS= read -r line; do
  src="${line%%:*}"
  rest="${line#*:}"
  link="${rest#*:}"
  # Extract the path inside ](...)
  target="$(printf '%s' "$link" | sed -nE 's/.*\]\(([^)]+)\).*/\1/p')"
  # Skip http(s), mailto, pure anchors
  case "$target" in
    http://*|https://*|mailto:*|'#'*) continue ;;
  esac
  # Strip trailing #anchor
  target="${target%%#*}"
  # URL-decode common encodings
  target=$(printf '%s' "$target" | sed 's/%20/ /g')
  # Resolve relative to the source file's directory
  src_dir="${src%/*}"
  case "$target" in
    /*) resolved="$target" ;;
    *)  resolved="$src_dir/$target" ;;
  esac
  total=$((total + 1))
  if [ ! -e "$resolved" ]; then
    printf 'BROKEN: %s -> %s\n' "$src" "$target"
    broken=$((broken + 1))
  fi
done < <(grep -rEn '\]\([^)]*\.md(#[^)]*)?\)' docs/ --include="*.md")
if [ "$broken" -eq 0 ]; then
  printf 'OK: 0 broken links (%d checked)\n' "$total"
fi
```

- **Clean output:** `OK: 0 broken links (NN checked)`
- **Failure output:** `BROKEN: docs/specs/foo.md -> ../missing.md` (one line per)
- **Known false positives:** None for the documented anchor / external /
  mailto cases. Templated links using shell-style placeholders
  (`{{var}}.md`) will register as broken — those should live in code-fenced
  examples, not real link expressions.

---

## 5. Find orphan markdown files

A file is **orphaned** when no other markdown file references it.

```bash
find docs -type f -name "*.md" -print | while IFS= read -r f; do
  base="${f##*/}"
  case "$base" in
    README.md) continue ;;  # indexes reference themselves implicitly
  esac
  # Count references to this basename across docs/
  count=$(grep -rEl "\\]\\([^)]*${base}\\b" docs/ --include="*.md" 2>/dev/null | grep -cv "^${f}$")
  if [ "${count:-0}" -eq 0 ]; then
    printf 'ORPHAN: %s\n' "$f"
  fi
done
```

- **Clean output:** (no lines printed)
- **Failure output:** `ORPHAN: docs/research/dropped-feature.md`
- **Known false positives:** Files referenced only from code (e.g. a doc
  linked from a Swift source comment) will show as orphans here. Either
  add them to a `README.md` index or accept the report.

---

## 6. Find index drift

Index files (`README.md`) sometimes reference deleted or renamed targets.

```bash
find docs -name "README.md" -print | while IFS= read -r idx; do
  idx_dir="${idx%/*}"
  grep -En '\]\([^)]*\.md\)' "$idx" | while IFS= read -r line; do
    target=$(printf '%s' "$line" | sed -nE 's/.*\]\(([^)]+\.md)(#[^)]*)?\).*/\1/p')
    case "$target" in http://*|https://*) continue ;; esac
    case "$target" in
      /*) resolved="$target" ;;
      *)  resolved="$idx_dir/$target" ;;
    esac
    if [ ! -e "$resolved" ]; then
      printf 'INDEX-DRIFT: %s references missing %s\n' "$idx" "$target"
    fi
  done
done
```

- **Clean output:** (no lines printed)
- **Failure output:** `INDEX-DRIFT: docs/specs/README.md references missing ui-old-toolbar-spec-deprecated.md`

---

## 7. Find case violations in filenames

```bash
find docs -type f -name "*.md" -print | grep -E '[A-Z]' | sed 's/^/CASE: /'
```

- **Clean output:** (no lines printed)
- **Failure output:** `CASE: docs/specs/Toolbar.md`

---

## 8. Find H1 / filename mismatch

The H1 inside a spec should match its rename. This is a soft check — the
H1 wording may legitimately differ from the slug.

```bash
find docs -type f -name "*.md" -print | while IFS= read -r f; do
  h1=$(grep -m1 -E '^# ' "$f" 2>/dev/null | sed 's/^# //' | tr 'A-Z' 'a-z' | tr -cd 'a-z0-9 ')
  base="${f##*/}"
  base="${base%.md}"
  # Compare a "main keyword" — middle segment of the slug
  mid=$(printf '%s' "$base" | awk -F- '{print $2}')
  if [ -n "$mid" ] && [ -n "$h1" ]; then
    if ! printf '%s' "$h1" | grep -q "$mid"; then
      printf 'H1-DRIFT: %s -> H1 "%s" missing slug token "%s"\n' "$f" "$h1" "$mid"
    fi
  fi
done
```

- **Clean output:** (no lines printed)
- **Failure output:** `H1-DRIFT: docs/specs/ui-toolbar-spec.md -> H1 "spec for navigation" missing slug token "toolbar"`
- **Known false positives:** Legitimate rewordings will trigger this.
  Treat as advisory.

---

## Composability with sibling skills

- **`bash-macos`** — These recipes are written to its portability rules
  (no `mapfile`, no GNU-only flags, no `readlink -f`). When adding new
  recipes, consult `bash-macos/SKILL.md` first.
- **`swift-file-splitting`** — The 600-line-per-doc cap in this skill
  mirrors the SwiftLint `file_length` cap that skill enforces for code.
