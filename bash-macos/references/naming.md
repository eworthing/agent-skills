# Script Naming Conventions

Name scripts using **lowercase snake_case** with **verb-first** structure.

## Core Rules

1. **Lowercase + underscores** -- `sync_logs.sh`, never `SyncLogs.sh` or `sync-logs.sh`
2. **Verb-first structure** -- `run_tests.sh`, `validate_config.py`, `build_image.sh`
3. **Max 4 words** -- `run_ui_tests.sh` ok, `run_all_ui_tests_for_platform.sh` too long
4. **Avoid builtins** -- never use `test`, `exec`, `time`, `kill`, `wait`

## Extension Rules

| Context | Extension | Example |
|---------|-----------|---------|
| Project-local scripts | **Include** `.sh`/`.py` | `./scripts/run_ui_tests.sh` |
| PATH-installed tools | **Omit** extension | `/usr/local/bin/deploy_config` |
| Git hooks | **None** (Git convention) | `pre-commit` |

## Common Verbs

| Verb | Purpose | Example |
|------|---------|---------|
| `run_` | Execute tests or processes | `run_ui_tests.sh` |
| `validate_` | Check correctness | `validate_skill.py` |
| `build_` | Compile or construct | `build_visual_audit_report.py` |
| `sync_` | Synchronize resources | `sync_skills.sh` |
| `install_` | Set up components | `install_hooks.sh` |
| `setup_` | Set up dev environment | `setup_dev.sh` |
| `check_` | Verify conditions | `check_accessibility.py` |
| `generate_` | Produce artifacts | `generate_report.sh` |

## Organization: Prefix vs Subdirectory

| Approach | Use When | Example |
|----------|----------|---------|
| **Verb prefix** | Scripts independently invoked | `run_ui_tests.sh`, `run_unit_tests.sh` |
| **Domain prefix** | Need quick tab-completion grouping | `audit_check_a11y.py`, `audit_score_parity.py` |
| **Subdirectory** | 4+ scripts with shared imports | `scripts/visual_audit/*.py` |

## Naming Checklist

- [ ] Lowercase with underscores?
- [ ] Starts with a verb?
- [ ] 4 words or fewer?
- [ ] No collision (`which {name}` returns nothing)?
- [ ] Not a shell builtin (`type {name}` returns nothing)?
