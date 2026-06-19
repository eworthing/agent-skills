# peer-plan-review Evaluation

**Date:** 2026-06-14
**Evaluator:** skill-evaluator-1.0.0 (Claude Opus 4.8)
**Skill version:** branch `refactor/ppr-common-migration` (+ Antigravity `agy` provider)
**Automated score:** 100% (13/13 checks passed).

---

## Automated Checks

```
📋 Skill Evaluation: peer-plan-review
  [STRUCTURE]     ✅ 5/5 — README.md allowed; _common/ + fixtures/ recognized
  [TRIGGER]       ✅ description with trigger phrases present
  [DOCUMENTATION] ✅ 176 body lines, all references linked
  [SCRIPTS]       ✅ all .py files parse clean
                  ✅ no external deps (_common is a local vendored package)
  [SECURITY]      ✅ no hardcoded creds
                  ✅ 2 env vars documented (references/env.md)
  Pass: 13  Warn: 0  Fail: 0  →  100%
```

Runtime probes:
- `--self-check` → providers found and healthy (codex not installed in this env; gemini/claude/copilot/opencode OK).
- `--list-models` → works.
- `pytest test_run_review.py test_web_search.py` → **118 passed** (incl. 2 agy execution tests).
- 6th provider — Antigravity (`agy`) — wired through the shared `PROVIDERS` registry + dedicated reference + `list_models_cmd`. Verified **live end-to-end**: round-1 + `--resume` round-2 through `run_review.py` (conversation id captured from the per-run `--log-file`; no workspace writes). opencode (5th) wired the same way.
- `python3 common/scripts/sync_common.py --check` → clean (vendored `_common/` byte-identical to source).

## Manual Assessment

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Completeness | 4/4 | 6 providers (codex/gemini/claude/copilot/opencode/`agy`; agy = Antigravity, successor to the EOL Gemini CLI), standard + adversarial stances, resume w/ fallback, `--list-models`, `--self-check`, `--summary-file`, structured output parsing, plan + reviewer metadata |
| 1.2 | Correctness | 4/4 | 118-test suite green; provider builders verified against April–June-2026 CLIs (agy v1.0.7 live round-trip incl. resume); `save_session()` is atomic (`.tmp` + rename), closes prior mid-round-crash gap; `datetime.UTC` (3.11-only) replaced with `timezone.utc` so the stated 3.9+ floor actually holds |
| 1.3 | Appropriateness | 4/4 | Python stdlib only, cross-platform (macOS/Linux/Windows), shared logic vendored from `common/` into `scripts/_common/` |
| 2.1 | Fault Tolerance | 4/4 | Auto resume→fresh fallback (logged), graceful structured-parse degradation, process-tree kill on timeout, SIGINT/SIGTERM handlers, Gemini config clone preserves auth, per-run Codex `CODEX_HOME` isolation (fail-closed) so concurrent same-repo reviews don't collide on session capture |
| 2.2 | Error Reporting | 3/4 | Clear stderr; structured JSONL `--error-log` retained after cleanup; still no global `--json` stdout mode, but `--summary-file` covers the machine-readable per-round case |
| 2.3 | Recoverability | 4/4 | Resume first-class; metadata records `resume_requested/attempted/fallback_used/reason`; error log survives cleanup |
| 3.1 | Token Cost | 4/4 | SKILL.md ~176 body lines. Output template, adversarial prompt, and adapter invocation details all live under `references/`. Lazy-loaded per provider |
| 3.2 | Execution Efficiency | 4/4 | One subprocess/round, stdout streamed, no polling |
| 4.1 | Learnability | 4/4 | SKILL.md walks the full loop concisely; provider refs lazy-loaded; `--self-check` and `--list-models` are explicit discovery paths |
| 4.2 | Consistency | 4/4 | Uniform CLI flags across all 5 providers; fresh vs resume differs only by `--resume`; same verdict contract everywhere |
| 4.3 | Feedback Quality | 4/4 | Progress per round to stderr; review header shows actual (not requested) model/effort/source; `--summary-file` writes `{verdict, model, effort, finding counts}` for non-Claude hosts |
| 4.4 | Error Prevention | 4/4 | `validate_prompt_file`, `probe_writable`, model-alias fuzzy-suggest, `--review-id` enforcement, preflight `--self-check` |
| 5.1 | Discoverability | 4/4 | argparse `--help`; `--list-models` and `--self-check` discoverable; top-level `README.md` for GitHub browsing, refreshed for the `_common/` layout + 116-test count |
| 5.2 | Forgiveness | 4/4 | Reviewer hard-pinned read-only; plan snapshots immutable per round; error log retained for post-mortem |
| 6.1 | Credential Handling | 4/4 | No hardcoded creds; `CODEX_HOME`, `GEMINI_CONFIG_DIR`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` documented in `references/env.md`; per-run Codex home copies `auth.json` (0600) into a randomized 0700 dir tracked in a symlink-proof (`O_NOFOLLOW`+`fstat`) manifest |
| 6.2 | Input Validation | 4/4 | File existence, UTF-8, non-empty, write-probe, model-alias validation, `--review-id` enforcement, effort enum clamping |
| 6.3 | Data Safety | 3/4 | codex `--sandbox read-only`; gemini `--sandbox`+yolo (tools only); claude `--permission-mode plan`; copilot `--deny-tool=write,shell,memory`; opencode read-only-by-prompt. **Exception: `agy`/Antigravity auto-approves file-write + shell in every flag combo — verified NOT read-only.** Mitigated (opt-in, experimental, `--sandbox` terminal containment, read-only directive prepended to the prompt, docs warn to run only on trusted/clean trees) but not guaranteed — hence −1. Transcript-share flags forbidden |
| 7.1 | Modularity | 4/4 | Shared logic vendored from `common/` into `scripts/_common/` (`session` / `log` / `process` / `metadata` / `providers`); skill keeps `run_review.py` + a thin `ppr_paths.py` CLI wrapper. One source of truth shared with quorum-review |
| 7.2 | Modifiability | 4/4 | Single `PROVIDERS` registry in `_common/providers/registry.py` (binary, effort_map, model_aliases, build_cmd, caps, optional `list_models_cmd`). Adding a 6th provider = one dict entry + one builder + one reference file. Edits go to `common/` source, then `sync_common.py` re-vendors |
| 7.3 | Testability | 4/4 | ~2000-line `test_run_review.py` + `test_web_search.py`; `scripts/fixtures/` with real provider JSON samples; deterministic via subprocess mocking; patch targets point at `_common.*` modules |
| 8.1 | Trigger Precision | 4/4 | 75-word description with explicit trigger phrases ("codex review", "gemini review", "opencode review", "pressure-test", "validate a plan"). No overlap with other review skills |
| 8.2 | Progressive Disclosure | 4/4 | Provider refs lazy-loaded; output-format/adversarial/adapter-cli/env each live in their own reference file. SKILL.md is a routing index |
| 8.3 | Composability | 4/4 | Bounded (read-only, no edits, explicit STOP). `agents/openai.yaml` wires `$peer-plan-review`. `scripts/fixtures/` flattened (no orphan `evals/` dir) |
| 8.4 | Idempotency | 4/4 | Session-based ID; atomic session save; resume is request-not-guarantee with auto-fallback; host can detect mid-loop state cleanly |
| 8.5 | Escape Hatches | 4/4 | `--self-check`, `--list-models`, `--timeout`, `--model`/`--effort` overrides, `--error-log`, `--resume` with explicit fallback visibility, `--summary-file` |
| | **TOTAL** | **98/100** | **Excellent — publish; `agy` is an opt-in, experimental, not-read-only reviewer** |

## Verdict

**Score: 98/100 — Excellent.** The lone deduction is Data Safety (6.3): the new opt-in `agy`/Antigravity reviewer is verified *not* read-only (it auto-approves tools), shipped experimental with sandbox + prompt-preamble mitigations and explicit warnings. Structural automated checks report a true 100% (the prior two false positives are resolved: `README.md` is allow-listed, and the dependency check recognizes the vendored `_common/` package as local rather than external).

The skill is structurally clean, well-tested (116 passing), defensively validated, atomic on session writes, single-edit-point for providers, lazy-loads every reference, and now shares its provider/session/process/metadata/log logic with quorum-review through the `common/` vendoring contract (no more duplicated `ppr_*` modules). There is no blocker to publishing.

## Priority Fixes

### P0 — Fix Before Publishing
*None.*

### P1 — Should Fix
*None.* (Prior P1s closed: env.md added, SKILL.md trimmed, session save atomic.)

### P2 — Nice to Have
*All previously listed P2s closed in the 2026-05-12 cleanup pass; see revision history below.*

## Revision History
| Date | Score | Notes |
|------|-------|-------|
| 2026-04-18 | 89/100 | Baseline eval — "Good", publishable with P1 cleanup |
| 2026-04-18 | — | P1 + P2 applied: env.md, SKILL.md 305→162 lines, atomic session save, provider registry (PROVIDERS dict), --summary-file, README.md, evals/fixtures→scripts/fixtures. Tests 79 → 87 passing. |
| 2026-05-12 | 99/100 | Re-evaluated post-rollup. 5th provider (opencode) integrated; tests 115 passing; SKILL.md body 147 lines; all 2026-04-18 P1s closed; only remaining P2s are doc-staleness + evaluator false positives. |
| 2026-05-12 | 100/100 | Final P2 cleanup. (1) README refreshed: 5 CLIs incl opencode, full `references/` listing, 115-test note. (2) `eval-skill.py` updated to allow `README.md` + ignore sibling-module imports — structural score 85% → 100%. (3) Legacy `BINARIES`/`EFFORT_MAP`/`MODEL_ALIASES`/`PROVIDER_CAPS`/`BUILDERS`/`_EFFORT_DEFAULTS` re-exports deleted from `ppr_providers.py`; all callers migrated to direct `PROVIDERS[name][key]` access. Tests: 114 passing (115 minus the now-obsolete `test_derived_views_match_registry`). |
| 2026-06-14 | 98/100 | Added 6th provider — Antigravity (`agy`), successor to the EOL-2026-06-18 Gemini CLI (Gemini retained for enterprise). New `build_agy_cmd` + registry entry + `extract_session_id_agy` (conversation id from a per-run `--log-file=`, parallel-safe), wired into both run_review.py adapters. Plain-text stdout (first non-JSON provider); effort encoded in the Gemini 3.5 Flash model name; resume via `--conversation`. Verified live (round-1 + resume; no workspace writes). **Data Safety 4→3:** agy auto-approves tools (not read-only) — shipped experimental with `--sandbox` + read-only prompt preamble + warnings. Tests 116 → **118**. |
| 2026-06-06 | 99/100 | Bug fix + `common/` migration. (1) Fixed `datetime.UTC` (Python 3.11-only) → `timezone.utc` at the `common/` source so the stated 3.9+ floor holds; re-synced both consumers. (2) Migrated to vendored `scripts/_common/` (session/log/process/metadata/providers), deleting the 5 duplicated `ppr_*.py`; `ppr_paths.py` kept as a thin CLI wrapper. Adopted `common`'s richer default Claude reviewer system prompt (reads referenced files before judging). (3) Light-touch SKILL.md prose pass (restored dropped articles/verbs in directive fragments). (4) `eval-skill.py` dependency check now treats local package dirs (`_common/`) as siblings — structural 100% for both `_common` consumers. Tests: **116 passing**. |
