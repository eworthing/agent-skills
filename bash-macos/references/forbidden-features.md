# Forbidden Bash 4+ Features on macOS

macOS ships Bash 3.2.x at `/bin/bash` for licensing reasons (Bash 4+ is GPLv3).
Scripts that must run on stock macOS cannot rely on any of the following.

## Feature Matrix

| Feature | Bash Version | Workaround |
|---------|--------------|------------|
| `declare -A` (associative arrays) | 4.0+ | Use indexed arrays or functions |
| `mapfile` / `readarray` | 4.0+ | Use `while read` loop |
| `${var,,}` lowercase | 4.0+ | Use `tr '[:upper:]' '[:lower:]'` |
| `${var^^}` uppercase | 4.0+ | Use `tr '[:lower:]' '[:upper:]'` |
| `shopt -s globstar` (`**`) | 4.0+ | Use `find` instead |
| `coproc` | 4.0+ | Use named pipes |
| `wait -n` | 4.3+ | Use `wait` without `-n` |
| `${parameter@operator}` transformations | 4.4+ | Avoid; use explicit conversions |
| `local -n` (nameref) | 4.3+ | Pass array by name + `eval` (rare) |

## Associative Array Workaround

```bash
# WRONG - Bash 4+ only
declare -A colors
colors["red"]="#FF0000"
echo "${colors[$key]}"

# CORRECT - Use functions or case statements
get_color() {
  case "$1" in
    red)   echo "#FF0000" ;;
    blue)  echo "#0000FF" ;;
    *)     echo "#000000" ;;
  esac
}
color=$(get_color "red")
```

For larger lookup sets, two parallel indexed arrays + a linear scan is fine for
small N (<100). For larger N, consider an external file or `awk`.

## mapfile / readarray Workaround

```bash
# WRONG - Bash 4+ only
mapfile -t lines < "$file"

# CORRECT - Works on Bash 3.2
lines=()
while IFS= read -r line; do
  lines+=("$line")
done < "$file"
```

The `IFS=` prevents leading/trailing whitespace stripping; `-r` prevents
backslash interpretation. Both flags are required to match `mapfile -t`
behavior.

## Case Conversion Workaround

```bash
# WRONG - Bash 4+ only
lower="${var,,}"
upper="${var^^}"

# CORRECT - portable
lower=$(printf '%s' "$var" | tr '[:upper:]' '[:lower:]')
upper=$(printf '%s' "$var" | tr '[:lower:]' '[:upper:]')
```

## Globstar Workaround

```bash
# WRONG - Bash 4+ only (with shopt -s globstar)
for f in src/**/*.sh; do ...

# CORRECT - find handles recursive globbing portably
while IFS= read -r -d '' f; do
  process "$f"
done < <(find src -name '*.sh' -print0)
```

`-print0` + `read -d ''` survives filenames with spaces and newlines.

## Detection

If you must conditionally use a Bash 4 feature:

```bash
if [[ "${BASH_VERSINFO[0]}" -ge 4 ]]; then
  declare -A map
else
  # fallback path
fi
```

Prefer writing the portable form unconditionally — it removes a branch and
matches the lowest-common-denominator behavior everywhere.
