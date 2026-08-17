# Skill Observation Log

Observations captured during task-oriented work. Each entry identifies a potential skill improvement or new skill opportunity.

**Status key:** OPEN = not yet actioned | ACTIONED = skill updated/created | DECLINED = user decided not to pursue

---

## 2026-07-13 — sub-agents comparison

### Observation 1: Replace stale OpenCode bypass with explicit read-only policy

**Status:** ACTIONED (`21aff80`; deny-key enforcement live-verified 2026-07-14 — see `peer-plan-review/SOURCES.md`)
**Date:** 2026-07-13
**Session context:** Compared shinpr/sub-agents-skills with peer-plan-review for transferable execution techniques.
**Skill:** peer-plan-review
**Type:** open-source
**Phase/Area:** Provider adapter / OpenCode safety and self-check
**Reference file:** `refs/competitors/peer-plan-review/sub-agents-skills/skills/sub-agents/scripts/_builder.py`

**Issue:** `peer-plan-review` still builds OpenCode commands with the now-absent `--dangerously-skip-permissions` flag and relies on prompt instructions for read-only behavior. Its self-check only runs top-level `opencode --help`, so it reported success even though `opencode run --help` exposes `--auto` instead. The competitor uses `--auto` plus an explicit `OPENCODE_PERMISSION` policy that denies edit, bash, task, external-directory, and question permissions.

**Suggested improvement:** Update `peer-plan-review`'s shared provider registry and OpenCode reference to use `opencode run --auto` with explicit read-only permission JSON in the child environment. Extend `self_check()` to inspect provider-subcommand help or otherwise validate the actual built flag surface, and add one command-builder/self-check regression test.

**Principle:** A headless adapter's health check must validate the invocation contract it actually uses; binary presence and generic help success do not catch removed flags or weakened permission semantics.

### Observation 2: Preserve bounded partial review output on timeout

**Status:** ACTIONED (`6a4f41b`; drain bounded via `drain_process`, 2026-07-14 audit pass)
**Date:** 2026-07-13
**Session context:** Compared shinpr/sub-agents-skills with peer-plan-review for transferable execution techniques.
**Skill:** peer-plan-review
**Type:** open-source
**Phase/Area:** Runner timeout and output handling
**Reference file:** `refs/competitors/peer-plan-review/sub-agents-skills/skills/sub-agents/scripts/_executor.py`

**Issue:** The competitor drains CLI output incrementally, normalizes terminal events, caps captured stdout, and returns a `partial` result when a timeout occurs after useful output. `peer-plan-review` uses `communicate(timeout=...)`, then discards the post-kill output on `TimeoutExpired`, so a long review can lose all usable findings and captured output is not memory-bounded.

**Suggested improvement:** In `peer-plan-review/scripts/run_review.py`, preserve timeout output before returning failure and record whether usable partial findings exist. Start with the smallest change—capture and write the `TimeoutExpired`/post-kill stdout to the existing artifacts and summary contract. Add full incremental normalization and an output ceiling only if real runs show hangs or excessive output.

**Principle:** Long-running agent adapters should distinguish failure with no result from interruption after a usable result, while bounding untrusted subprocess output.

---

## 2026-07-14 — full-skill audit pass (deliberate follow-ups)

### Observation 3: Reconcile the two structured-review grammars

**Status:** OPEN
**Date:** 2026-07-14
**Skill:** peer-plan-review + quorum-review (`common/`)
**Phase/Area:** Output parsing (`common/session/io.py` vs quorum's tier-2 parser)

**Issue:** The two consumers parse reviewer output with deliberately different grammars (verdict position, section fallback, finding shape, telemetry). The 2026-07-14 pass converged the tolerable-verdict shapes in `common/` (wrappers, backticks, casing), but the remaining deltas are undocumented — a reviewer output can parse in one consumer and not the other.

**Suggested improvement:** Reconcile the two grammars' deliberate deltas or document them as intentional per-consumer contracts (one comparison table in `common/` docs).

**Principle:** Two parsers for one wire format need either convergence or a written contract; silent divergence turns provider quirks into consumer-specific bugs.

### Observation 4: `check_shim_contract.py` is dead tooling as wired

**Status:** OPEN
**Date:** 2026-07-14
**Skill:** repo infrastructure (`common/scripts/check_shim_contract.py`)

**Issue:** No CI workflow or hook invokes `check_shim_contract.py`; the root `CLAUDE.md` claims it as one of the three CI scripts. Either wire it into the pre-commit hook/CI or correct the claim.

**Principle:** A validator that nothing runs is documentation, not enforcement.

### Observation 5: Quorum-side ports of peer hardening

**Status:** OPEN
**Date:** 2026-07-14
**Skill:** quorum-review

**Issue:** Peer-only hardening that quorum could adopt: `probe_writable`/`validate_prompt_file` preflight use, and a non-recursive resume fallback (quorum's resume fallback re-enters `run_review` recursively). The 2026-07-14 pass already gave quorum the shared `drain_process` and the codex-home refresh/sweep.

**Principle:** When two consumers share a transport layer, hardening one side leaves the other as the weakest link until ported or declined explicitly.
