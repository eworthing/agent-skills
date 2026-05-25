# common — shared infrastructure for agent skills

This package is the **source of truth** for code shared across skills in this repo. Today the only consumer is `quorum-review` (which migrated in v3.1). `peer-plan-review` still owns the original `ppr_*.py` modules; migration deferred per the v3.1 refactor plan's Phase F.

## Layout

```
common/
├── __init__.py
├── providers/registry.py     # PROVIDERS dict, build_*_cmd, get_provider(allowed=...)
├── metadata/extractors.py    # session-id parsers, extract_metadata, compute_plan_metadata
├── session/io.py             # load_session/save_session, extract_text_from_output, parse_structured_review
├── session/paths.py          # canonical temp-file paths (also a standalone CLI)
├── process/tree.py           # process-group kill, popen kwargs
├── log/events.py             # JSONL EventLogger
└── tests/                    # canonical tests against this source — see below
```

## Distribution model — vendored

Each consumer skill **vendors** a copy under `<skill>/scripts/_common/`. The vendored tree is **committed**. At runtime, the skill's scripts import from the sibling vendored tree:

```python
# quorum-review/scripts/run_review.py
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))  # so "_common" resolves
from _common.providers.registry import get_provider, PROVIDERS
```

Why vendor instead of `sys.path` walk-up to the repo root?

- **Standalone installs work.** A skill installed via `npx skills add` or copied to a machine without the `agent-skills` repo present must still resolve its imports. The vendored copy lives next to the script.
- **Symlink installs work.** `~/.claude/skills/<skill>` is typically a symlink into this repo; `__file__` resolution through symlinks reaches the real script, and `_common/` is a sibling.
- **CI sandboxes work.** No repo-root assumption.

## Drift control — enforced, not advised

Direct edits to vendored `_common/` trees would silently fork. Three layers prevent this:

1. **Pre-commit hook** (`.githooks/pre-commit`): runs `python3 common/scripts/sync_common.py --check`. The check **regenerates** each `_common/` from `common/common/` in memory and **diffs** against on-disk. Fails on any divergence: source-changed-without-resync, direct edit, OR extra file under `_common/` (no orphan `.pyc`, no half-removed files). Also runs `check_module_size.py` against any consumer's split `quorum/` package.
2. **CI gate**: same `sync_common.py --check` runs on every push. Catches contributors who bypassed pre-commit with `--no-verify` or never installed it.
3. **Canonical tests**: live in `common/tests/`, run against `common/common/` (the source). Each consumer's vendored copy is byte-identical by construction, so re-running the tests against it would be redundant. The CI runs a smoke import test against each vendored tree to confirm it loads.

### Installing the pre-commit hook

Run once per clone (per maintainer):

```bash
git config core.hooksPath .githooks
```

Then every `git commit` runs the gate. To bypass for a one-off WIP commit (not for merges):

```bash
git commit --no-verify -m "wip"
```

The CI gate will still run, so `--no-verify` commits will fail CI if they drift the vendored tree.

## To sync a skill after editing common/

```bash
python3 common/scripts/sync_common.py
git add common/ <skill>/scripts/_common/
git commit -m "..."
```

`sync_common.py` discovers every skill with an existing `_common/` and regenerates them. Use `--skill <name>` to limit to one.

## To add a new consumer skill

```bash
mkdir -p <new-skill>/scripts/_common
python3 common/scripts/sync_common.py --skill <new-skill>
git add <new-skill>/scripts/_common/
```

Then import from `_common.*` in the skill's scripts (after adding the `sys.path.insert` snippet shown above).
