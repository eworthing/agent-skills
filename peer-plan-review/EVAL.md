# peer-plan-review Evaluation

**Date:** 2026-04-18
**Evaluator:** skill-evaluator-1.0.0 (Claude Opus 4.7)
**Skill version:** HEAD @ 36e86df (working tree clean for peer-plan-review/)
**Automated score:** 85% (11/13 checks passed, 2 warnings)

---

## Automated Checks

```
📋 Skill Evaluation: peer-plan-review
  [STRUCTURE]     ✅ all 5 checks
  [TRIGGER]       ✅ desc 72 words, triggers present
  [DOCUMENTATION] ✅ 295 lines, references linked
  [SCRIPTS]       ✅ 7 py files parse clean
                  ⚠️  test_run_review imports run_review/ppr_* — internal-only
                     (false positive — these are sibling modules, not external deps)
  [SECURITY]      ✅ no hardcoded creds
                  ⚠️  CODEX_HOME, GEMINI_CONFIG_DIR read but not documented
  Pass: 11  Warn: 2  Fail: 0  →  85%
```

Runtime probes:
- `--self-check` → all 4 providers found and healthy
- `--list-models` → works for all providers, clean output
- `pytest test_run_review.py` → 79 passed
- Module graph indexed cleanly via codebase-memory.

## Manual Assessment

| # | Criterion | Score | Notes |
|---|-----------|-------|-------|
| 1.1 | Completeness | 4/4 | 4 providers, standard + adversarial stances, resume w/ fallback, --list-models, --self-check, --model/--effort, structured output parsing, plan metadata |
| 1.2 | Correctness | 3/4 | 79-test suite green; provider command builders verified against March-2026 CLIs. One rough edge: session-file truncation before each round means a mid-round crash loses prior round's session_id |
| 1.3 | Appropriateness | 4/4 | Python stdlib only, cross-platform (explicit Windows support in history), modular via ppr_* packages |
| 2.1 | Fault Tolerance | 4/4 | Automatic resume→fresh fallback (logged), structured-parse graceful degradation, timeout handling with process-tree kill, signal handlers for SIGINT/SIGTERM, Gemini config clone preserves auth |
| 2.2 | Error Reporting | 3/4 | Clear stderr with actionable messages; structured JSONL error log (`--error-log`) with timestamped events; no global `--json` mode for stdout but not needed for this shape |
| 2.3 | Recoverability | 4/4 | Resume is first-class; session metadata records resume_requested/attempted/fallback_used/reason; error log intentionally retained after cleanup |
| 3.1 | Token Cost | 2/4 | **SKILL.md is 295 lines** — verbose for its job. Round-1/revise sections duplicate the adapter invocation block; the structured-output template could move to a reference file. Target: ~180 lines |
| 3.2 | Execution Efficiency | 4/4 | Single subprocess per round, no polling, stdout streamed, no redundant API calls |
| 4.1 | Learnability | 4/4 | SKILL.md walks the full loop; provider refs lazy-loaded after reviewer choice; --self-check and --list-models are explicit discovery paths |
| 4.2 | Consistency | 4/4 | Uniform CLI flags across providers; fresh/resume invocation differs only by `--resume`; same verdict contract and output template across all four |
| 4.3 | Feedback Quality | 3/4 | Progress line per round to stderr; review header shows actual (not requested) model+effort+source; no per-round summary table in adapter itself (host agent renders it from ppr_io.parse_structured_review) |
| 4.4 | Error Prevention | 4/4 | validate_prompt_file (exists/readable/utf8/non-empty), probe_writable for output paths, model-alias validation with fuzzy-suggest, --review-id required with --error-log, preflight self-check |
| 5.1 | Discoverability | 3/4 | argparse --help covers flags; --list-models and --self-check are discoverable. No top-level README.md in skill root; users depend on SKILL.md + provider refs |
| 5.2 | Forgiveness | 4/4 | Reviewer is read-only by design (sandbox flags baked into builders); plan snapshots immutable per round; error log survives cleanup for post-mortem |
| 6.1 | Credential Handling | 3/4 | No hardcoded creds. **Gap:** CODEX_HOME and GEMINI_CONFIG_DIR are read but not documented in SKILL.md — users cloning the skill won't know these exist |
| 6.2 | Input Validation | 4/4 | File existence, UTF-8, non-empty, write-probe, model-alias validation, --review-id enforcement, effort enum clamping |
| 6.3 | Data Safety | 4/4 | Each provider invocation hard-pins read-only: codex `--sandbox read-only` + `approval_mode=never`; gemini `--sandbox` + yolo (tools only); claude `--permission-mode plan`; copilot `--deny-tool=write,shell,memory`. Transcript-sharing flags explicitly forbidden |
| 7.1 | Modularity | 4/4 | Clean split: `ppr_io` (IO/parse), `ppr_log` (events), `ppr_metadata` (extraction), `ppr_providers` (command builders), `run_review` (orchestration). 585-line runner is dense but scopes concerns well |
| 7.2 | Modifiability | 3/4 | Adding a provider requires touching BINARIES, EFFORT_MAP, PROVIDER_CAPS, builders dict, MODEL_ALIASES, extract_session_id_*, and a new references/*.md — spread across 2 files. Could be consolidated into a provider class |
| 7.3 | Testability | 4/4 | 1361-line test suite (test_run_review.py) + 370-line test_web_search.py; evals/fixtures/ with real provider JSON samples; deterministic via subprocess mocking |
| 8.1 | Trigger Precision | 4/4 | 72-word description with explicit trigger phrases ("codex review", "gemini review", "pressure-test", "validate a plan"). No overlap with other review skills |
| 8.2 | Progressive Disclosure | 3/4 | Provider refs correctly lazy-loaded. But SKILL.md inlines the full structured-output template, adversarial prompt template, and two ~10-line adapter invocation blocks — those could be references |
| 8.3 | Composability | 3/4 | Skill is bounded (read-only, no file edits, explicit STOP before implementation). `agents/openai.yaml` wires it for `$peer-plan-review`. Minor: `evals/fixtures/` is the only child of `evals/` — could live under `scripts/fixtures/` |
| 8.4 | Idempotency | 4/4 | Session-based ID; output file truncated before each write; resume is request-not-guarantee with auto-fallback; session metadata lets host detect mid-loop state cleanly |
| 8.5 | Escape Hatches | 4/4 | --self-check, --list-models, --timeout, --model override, --effort override, --error-log, --resume with explicit fallback visibility |
| | **TOTAL** | **89/100** | **Good — publishable, with noted issues** |

## Verdict

**Score: 89/100 — Good.** Publishable. The skill is structurally clean, well-tested, defensively validated, and the automation probes (self-check, tests, list-models) all succeed on the current system. The "not working as expected" framing isn't borne out by runtime evidence on this machine — everything the skill claims to do, it does. If there's a specific failure the user has seen, it will show up in `ppr-<id>-errors.jsonl` after a run, and that log is the right starting point rather than speculation.

Real gaps below are **correctness-adjacent or cosmetic**, not "broken."

## Priority Fixes

### P0 — Fix Before Publishing
*None.* No blocking issues. All automated checks pass and no unhandled failure paths found.

### P1 — Should Fix

1. **Document CODEX_HOME and GEMINI_CONFIG_DIR in SKILL.md or a new `references/env.md`.** Currently `run_review.py` reads both but SKILL.md never mentions them. Users who want to point at non-default config dirs have to read source.

2. **Trim SKILL.md from 295 → ~180 lines** by moving to references:
   - The full `### Reasoning / Blocking Issues / Non-Blocking Issues` output template (it's repeated in spirit in the adversarial prompt section) → `references/output-format.md`
   - The adversarial prompt template (lines 74-91) → `references/adversarial.md`
   - Consolidate the two near-identical adapter invocation code blocks (Round 1 vs Revise) into one reference with a `--resume` note
   Each round currently pays tokens twice for the same adapter invocation structure.

3. **Session-file durability on mid-round crash.** `load_session()` reads, the runner eventually calls `save_session()` at end. If a provider crashes between `proc.communicate` and `save_session`, the prior round's session_id is lost because the output file has already been truncated. Mitigation: write a `*.tmp` session snapshot at run start, rename on success.

### P2 — Nice to Have

1. **Consolidate provider plumbing.** Adding a 5th provider today means editing ~7 call sites across `run_review.py` + `ppr_providers.py` + `ppr_metadata.py`. A `Provider` dataclass (binary, caps, builder, session_extractor, metadata_extractor) keyed into one registry dict would collapse that to one edit.

2. **Flatten `evals/fixtures/` to `scripts/fixtures/`.** `evals/` currently contains only the `fixtures/` subdir. The evaluator warned about this as a directory-empty candidate; either add real eval harnesses or flatten.

3. **Add a top-level `README.md`** for GitHub browsing. SKILL.md is agent-facing; a 40-line README aimed at humans would help human contributors without bloating the agent-facing doc.

4. **Emit a machine-readable per-round summary.** Today the review header is rendered by the host agent. A `--summary-file` that the adapter writes with `{verdict, model, effort, finding_count, blocking_count}` would let non-Claude hosts adopt the skill without reimplementing `parse_structured_review` externally.

## Revision History
| Date | Score | Notes |
|------|-------|-------|
| 2026-04-18 | 89/100 | Baseline eval — "Good", publishable with P1 cleanup |
| 2026-04-18 | — | P1 + P2 applied: env.md, SKILL.md 305→162 lines, atomic session save, provider registry (PROVIDERS dict), --summary-file, README.md, evals/fixtures→scripts/fixtures. Tests 79 → 87 passing. Structural score still 85% (remaining warnings are false positives: sibling-module imports flagged as external deps). |
