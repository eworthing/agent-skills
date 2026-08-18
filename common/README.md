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

## eval-guard — skill-prose changes need a guarding eval

**The rule:** a substantive change to a skill's `SKILL.md` or `references/*.md` must either touch that skill's `evals/` (or `tests/`) directory, or add/modify a `scripts/_*selftest*.py` (or `scripts/*_selftest.py`) file — this repo's convention for a deterministic prose guard that doesn't live under `evals/`/`tests/`, e.g. `contest-refactor/scripts/_ingress_envelope_selftest.py` — in the same change, or carry an explicit `Eval-waiver: <reason>` commit trailer. This was already the repo's standing discipline, unenforced; `common/scripts/eval_guard.py` is what enforces it mechanically instead of relying on memory.

**Selftest touch, mechanically:** counts only an added-or-modified file matching the pattern above under that skill's `scripts/`; a pure deletion doesn't count (removing the guarding test isn't coverage), and a selftest under a different skill doesn't satisfy this skill's gate.

**"Substantive," mechanically:** the diff has to reach beyond the YAML frontmatter block and beyond whitespace-only edits. Bumping a frontmatter field (a version, `allowed-tools`) or reflowing whitespace doesn't count; anything else in the body does. Additions and deletions fall out of the same rule for free — a deletion's new side is empty text, which can't equal a non-trivial stripped-and-normalized body, so deleting prose with no eval touch is always flagged. Renames are diffed by content at their old/new paths, so a pure rename (no content change) passes and a rename-with-rewrite is judged on the rewrite. When in doubt, the classifier errs toward flagging.

**Waiver format:** a git trailer, `Eval-waiver: <reason>` (exact key spelling, non-empty reason), in the trailing trailer block of the commit message — the same convention this repo already uses for `Co-Authored-By:` / `Claude-Session:`. A malformed near-miss (wrong case, empty reason) is reported but does not count as a waiver.

**Three-part contract** (this repo commits straight to `main`, so there's no PR gate to lean on):

1. **pre-commit** (`.githooks/pre-commit`, Gate 4) runs `eval_guard.py --staged` — catches the common path early. It is advisory only and always exits 0 on policy grounds: git invokes pre-commit *before* obtaining the commit message, so this stage structurally cannot see a waiver trailer and must never block on its absence.
2. **commit-msg** (`.githooks/commit-msg`, new hook) runs `eval_guard.py --commit-msg "$1"` — the real local gate, since by now both the staged diff and the drafted message (with any trailer) exist.
3. **CI** (`.github/workflows/eval-guard.yml`, new workflow — none existed before this change) runs `eval_guard.py --range <base>..<head>` on every push/PR — catches anything that bypassed 1/2 (`--no-verify`, `core.hooksPath` never configured, a merge, ...) once it has landed.

All three modes share one checker script (`common/scripts/eval_guard.py`), so the "substantive" and waiver logic can't drift between local and CI.

**Report-only today.** `eval_guard.py`'s `REPORT_ONLY = True` constant makes every policy failure print a loud warning and exit 0 instead of blocking — verified live against this repo's own commit history while building the gate (it correctly flagged a real past `contest-refactor` commit that touched `SKILL.md`/`references/` with no eval touch, and correctly passed one that did touch evals). **The flip:** set `REPORT_ONLY = False` in `common/scripts/eval_guard.py` (or pass `--enforce` explicitly to the commit-msg/CI invocations) to make `commit-msg` and CI actually block on exit code 1. `--staged` never blocks regardless — that's structural, not a report-only artifact — so pre-commit stays a nudge even after the flip.

**Containment step on a red CI check:** either revert the offending commit, or land an immediate follow-up commit — an empty commit is fine — that adds the missing `evals/`/`tests/` (or `scripts/_*selftest*.py`) coverage, or adds a properly formatted `Eval-waiver: <reason>` trailer.

**Exit codes** (shared discipline with `sync_common.py --check` / `check_module_size.py`): `0` pass, `1` policy fail (downgraded to `0` under report-only), `2` plumbing error (bad args, a git command itself failed, ...) — plumbing errors are never downgraded, so a broken checker still surfaces instead of silently no-op'ing.

Tests: `common/tests/test_eval_guard.py` (throwaway git repos under `tmp_path`, one per fixture case: substantive-without-touch, substantive-with-touch, substantive-with-selftest-touch, substantive-with-unrelated-scripts-file, frontmatter-only, whitespace-only, valid waiver, malformed waiver, rename, deletion, report-only downgrade, `--staged` advisory-only, plumbing errors).
