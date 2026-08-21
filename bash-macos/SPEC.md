# Bash macOS Compatibility Skill Specification

## Intent

`bash-macos` provides the canonical guidelines, patterns, and deterministic verification gates to ensure shell scripts run portably across macOS (stock `/bin/bash` 3.2.57, BSD userland) and modern Linux (Bash 4.4+/5.x, GNU coreutils).

Its primary purpose is to prevent scripts written in this repository or generated for developer environments from failing due to Bash 4+ syntax dependencies (`mapfile`, `declare -A`, `${var,,}`, `shopt -s globstar`, `|&`) or BSD vs GNU coreutils flag differences (`sed -i`, `sed -r`, `grep -P`, `date -d`, `stat -c`, `base64 -w`).

## Scope

In scope:

- Writing, modifying, and reviewing shell scripts (`*.sh`) intended to run on macOS developer workstations and Linux CI environments.
- Enforcing Bash 3.2.57 compatibility for `/bin/bash` scripts without requiring POSIX `/bin/sh` degradation.
- Bridging BSD vs GNU userland divergences (sed, grep, date, stat, find, xargs, base64, readlink/realpath).
- Portable script architecture: strict mode (`set -euo pipefail`), subshell trap propagation (`set -E`), safe temp file handling (`mktemp`, `trap cleanup EXIT INT TERM`), long option parsing, and dry-run patterns.
- Script naming conventions (lowercase snake_case, verb-first).
- 3-mode output logging (compact, verbose, raw) for multi-stage automation scripts.
- Deterministic static validation via `scripts/validate_portability.py`.

Out of scope:

- Writing scripts targeting `/bin/zsh` (macOS default interactive login shell) — `bash-macos` targets `/bin/bash` scripts explicitly.
- Forcing POSIX `/bin/sh` compatibility when Bash 3.2 features (`[[ ... ]]`, indexed arrays, `local`, process substitution `<(...)`) are appropriate.
- Introducing third-party language dependencies (e.g., Python, Node, Ruby, Homebrew GNU binaries) for basic shell script execution.

## Users And Trigger Context

- Primary users: Agents and software engineers authoring, editing, or debugging shell scripts.
- Primary triggers:
  - Writing or updating any `*.sh` script.
  - Encountering runtime errors on macOS: `mapfile: command not found`, `declare: -A: invalid option`, `sed: illegal option -- r`, `grep: invalid option -- P`, `date: illegal option -- d`.
  - Porting Linux/GNU shell scripts to macOS.
  - Reviewing shell script naming and repository script organization.
- Non-triggers:
  - Direct Zsh interactive config (`.zshrc`, `.zprofile`).
  - Pure Python or Node CLI tools that do not execute shell subcommands.

## Runtime Contract

- Invariants:
  - Shebang must be `#!/bin/bash` accompanied by a version guard for Bash ≥ 3.
  - Strict mode enabled by default: `set -euo pipefail`. If `-e` is omitted for scanner/audit scripts branching on intentional non-zero exits (e.g. `grep`), the header must document it explicitly.
  - Zero Bash 4+ features: no `declare -A`, `mapfile`/`readarray`, `${var,,}`/`${var^^}`, `shopt -s globstar`, `coproc`, `wait -n`, `local -n`, `|&`.
  - Zero unportable GNU flags: use `sed -E` (not `sed -r`), atomic temp-mv instead of unportable `sed -i`, `grep -E` (not `grep -P`), `date -v` or epoch math (not `date -d`), `stat -f` (not `stat -c`), `base64 | tr -d '\n'` (not `base64 -w 0`).
  - Destructive operations gated behind a centralized `run_cmd` dry-run wrapper.
  - Temporary files created in `$TMPDIR` and cleaned up deterministically via `trap cleanup EXIT INT TERM`.
  - Script names must use lowercase snake_case with verb-first phrasing (max 4 words).

- Verification Gates:
  - Static parse: `bash -n <script.sh>`
  - Static lint: `shellcheck -s bash <script.sh>`
  - Portability scan: `python3 scripts/validate_portability.py <script.sh>`
  - Native execution test: `/bin/bash <script.sh> --help` or `--dry-run`

## Reference Architecture

- `SKILL.md`: Lean runtime router (~220–250 lines) containing high-frequency matrices, strict mode invariants, safe script patterns, and verification gates.
- `references/forbidden-features.md`: Complete matrix of Bash 4+ features with drop-in Bash 3.2 portable replacements.
- `references/template.md`: Production-ready starter scaffold with CLI argument parsing, safe temp files, and dry-run execution.
- `references/output-modes.md`: Standardized 3-mode output harness (`compact`, `--verbose`, `--raw`) for multi-stage automation scripts.
- `references/naming.md`: Authoritative verb catalog, extension rules, and prefix/directory organization rules.
- `scripts/validate_portability.py`: Standalone, zero-dependency Python 3 static analyzer for automated portability enforcement.

## Platform Ground Truth & History

- macOS Darwin Baseline:
  - macOS 10.13 through macOS 27+ (Darwin 27): `/bin/bash` remains frozen at version `3.2.57(1)-release` (GPLv2).
  - macOS 13+ (Ventura): `/bin/realpath` and `readlink -f` ship natively.
  - `/usr/bin/python3` on macOS is an Xcode Command Line Tools stub; shell scripts must not depend on it for fundamental script execution.
