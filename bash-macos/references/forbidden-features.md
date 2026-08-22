# Forbidden Bash 4+ Features on macOS

macOS ships Bash 3.2.x at `/bin/bash` for licensing reasons (Bash 4+ is GPLv3).
Scripts that must run on stock macOS cannot rely on any of the following features.

## Feature Matrix

| Feature | Bash Version | Workaround |
|---------|--------------|------------|
| `declare -A` (associative arrays) | 4.0+ | Use indexed arrays or case statement lookup functions |
| `mapfile` / `readarray` | 4.0+ | Use `while IFS= read -r` loop |
| `${var,,}` lowercase | 4.0+ | Use `printf '%s' "$var" \| tr '[:upper:]' '[:lower:]'` |
| `${var^^}` uppercase | 4.0+ | Use `printf '%s' "$var" \| tr '[:lower:]' '[:upper:]'` |
| `shopt -s globstar` (`**`) | 4.0+ | Use `find` with `-name` and `-print0` |
| `\|&` (pipe stdout and stderr) | 4.0+ | Use `2>&1 \|` |
| `coproc` | 4.0+ | Use named pipes (`mkfifo`) or subshells |
| `wait -n` | 4.3+ | Use `wait` without `-n` |
| `local -n` (nameref) | 4.3+ | Pass array by name or design function boundaries cleanly |
| `${arr[-1]}` (negative index) | 4.3+ | Use `${arr[$((${#arr[@]}-1))]}` |
| `[[ -v var ]]` (test if set) | 4.2+ | Use `[[ -n "${var+x}" ]]` |
| `${parameter@operator}` transformations | 4.4+ | Avoid; use explicit conversions |
| `head -n -N` (negative line counts) | GNU coreutils | Use `sed '$d'` or `sed -e :a -e '$d;N;2,3ba' -e 'P;D'` |
| `base64 -w 0` (no line wrap) | GNU coreutils | Use `base64 \| tr -d '\n'` |

## Associative Array Workaround

### Pattern 1: Function / Case Statement Dispatch (Best for fixed keys)

```bash
# WRONG - Bash 4+ only
declare -A colors
colors["red"]="#FF0000"
colors["blue"]="#0000FF"
echo "${colors[$key]}"

# CORRECT - Portable Bash 3.2 function
get_color() {
  case "$1" in
    red)   echo "#FF0000" ;;
    blue)  echo "#0000FF" ;;
    *)     echo "#000000" ;;
  esac
}
color=$(get_color "red")
```

### Pattern 2: Parallel Indexed Arrays (For dynamic keys < 100 entries)

```bash
keys=()
values=()

map_set() {
  local k="$1" v="$2"
  keys+=("$k")
  values+=("$v")
}

map_get() {
  local target="$1" i
  for ((i=0; i<${#keys[@]}; i++)); do
    if [[ "${keys[i]}" == "$target" ]]; then
      printf '%s\n' "${values[i]}"
      return 0
    fi
  done
  return 1
}
```

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

The `IFS=` prevents leading/trailing whitespace stripping; `-r` prevents backslash interpretation. Both flags are required to match `mapfile -t` behavior.

## Case Conversion Workaround

```bash
# WRONG - Bash 4+ only
lower="${var,,}"
upper="${var^^}"

# CORRECT - Portable
lower=$(printf '%s' "$var" | tr '[:upper:]' '[:lower:]')
upper=$(printf '%s' "$var" | tr '[:lower:]' '[:upper:]')
```

## Globstar Workaround

```bash
# WRONG - Bash 4+ only (with shopt -s globstar)
for f in src/**/*.sh; do
  process "$f"
done

# CORRECT - find handles recursive globbing portably
while IFS= read -r -d '' f; do
  process "$f"
done < <(find src -name '*.sh' -print0)
```

`-print0` + `read -d ''` survives filenames containing spaces, tabs, and newlines.

## Pipe Stderr Workaround (`|&`)

```bash
# WRONG - Bash 4+ only
cmd1 |& cmd2

# CORRECT - Portable
cmd1 2>&1 | cmd2
```

## Detection

If you must conditionally support a Bash 4 feature:

```bash
if [[ "${BASH_VERSINFO[0]}" -ge 4 ]]; then
  declare -A map
else
  : # fallback path
fi
```

Prefer writing the portable form unconditionally — it eliminates branching and ensures consistent behavior across all machines.
