# Changelog — quorum-review

## v3.1 — Internal refactor (May 2026)

Structural cleanup; **CLI, ledger schema, verdict semantics, merge classifications, and verifier contract are unchanged**.

### Added

- `scripts/_common/` — vendored copy of the shared infrastructure in `/common/` at the repo root (provider registry, metadata extractors, session I/O, process management, JSONL event logging). Synced via `python3 common/scripts/sync_common.py`. Pre-commit + CI enforce byte-identical vendoring.
- `scripts/accepted_reviewers.py` — single source-of-truth allow-list (`ACCEPTED_REVIEWERS`). Every CLI-facing path (argparse, `--list-models`, `--self-check`, `--help`, error messages, internal dispatch) routes through `accepted_reviewers()` so opencode (present in the shared `PROVIDERS` registry for other consumers) cannot leak into quorum-review's surface.
- `scripts/quorum/` package — the orchestrator implementation, split into 7 modules per responsibility:
  - `cli.py` — argparse, validators, threshold/failure-mode policy, verifier resolution
  - `orchestrator.py` — `main()`, round-loop, reviewer dispatch, early-exit logic
  - `ledger.py` — CRUD, canonical IDs, v2 → v3 alias migration
  - `parsing.py` — verdict/structured-review/cross-critique/anchor parsers + telemetry
  - `merge.py` — `classify_pair` (4 classes), merge pipeline, merge-log JSONL
  - `verification.py` — external verifier dispatch + VERIFIED/INVALIDATED parse
  - `prompts.py` — initial / deliberation / verification prompt templates + role packs
- `scripts/run_quorum.py` is now a compatibility shim re-exporting every name `test_run_quorum.py` imports (43 names, AST-verified by `common/scripts/check_shim_contract.py`).
- `CONTRIBUTING.md` — reviewer checklist for keeping `parsing.py` and `prompts.py` from re-monolithizing.
- `EVAL.md` — pre-refactor baseline against the skill-evaluator rubric.
- `tests/fixtures/mid-quorum-r3/` — live round-3-of-5 fixture for the resume gate (round-4 expected snapshots in `mid-quorum-r4-expected/`).
- `scripts/tests/test_parsing_variants.py` — Phase-D parser hardening tests (Tier-1 strict, Tier-2 variants, telemetry isolation, parser_name multiset assertion).
- `references/output-format.md` — reviewer output template + code anchors + round-2+ cross-critique + blind-mode notes.

### Changed

- **Parser hardening**: reviewer-output parsers (`parse_verdict` and friends) use a two-tier scheme.
  - Tier 1: exact contract match (unchanged behavior).
  - Tier 2: explicit syntactic variants (case-insensitive, whitespace-tolerant, trailing punctuation).
  - No Tier 3 keyword heuristic — total failure returns `None` (caller treats as REVISE per v2.1 contract) and logs to `qr-${QUORUM_ID}-parse-failures.jsonl` (overridable via `QUORUM_PARSE_FAILURES_LOG` env var).
- **`scripts/run_review.py` rewritten** from 939 LoC monolith to ~530 LoC consumer of `_common/`. Behavior unchanged. Added `--verification-mode` support to the shared `build_claude_cmd` (gated by `getattr(args, "verification_mode", False)`; harmless to other consumers).
- **Documentation split**: `SKILL.md` now points to the references via a `## Bundled resources` index (previously the references existed but were unlinked, flagged as a warning by `eval-skill.py`). `protocol.md` slimmed to authoritative machine contracts only (the round-flow / role-packs / cross-critique syntax that previously duplicated `SKILL.md` moved to `output-format.md` or were de-duplicated).

### Tooling (in `/common/scripts/`)

- `sync_common.py` — vendor `common/common/` into each consumer skill's `scripts/_common/`. `--check` regenerates in-memory and diffs against on-disk; rejects extra files (no orphan `.pyc`, no half-removed files). Used by pre-commit and CI.
- `check_shim_contract.py` — AST scan of any test file to enumerate the names a compatibility shim must re-export. Handles multiline imports, `import X then X.attr`, `mock.patch("X.attr")`, `patch.object(X, "attr")`, literal `getattr(X, "attr")`. Rejects star imports and dynamic `getattr` with line numbers (must be refactored before shim analysis).
- `check_module_size.py` — soft cap (600 LoC, warning) and hard cap (800 LoC, fail) per module. Hard cap is escapable via an explicit `# WAIVER: module-size <reason>` comment in the first 20 lines, so reviewers see the waiver in PR diffs.

### Not changed

- CLI flag set, flag semantics, exit codes.
- Accepted provider set: `{claude, gemini, codex, copilot}`.
- Ledger JSON schema (every field in `references/protocol.md` "Core shape" preserved); v3 ledgers load and round-trip byte-identically.
- Merge classifications (4 classes, same rules).
- Verdict derivation from surviving blockers; same `support_count` / `dispute_count` math.
- Verifier first-line contract (`VERIFIED <ID>` / `INVALIDATED <ID>`).
- Reviewer anonymization: stable `Reviewer A/B/C` labels per quorum, by index. Per-round rotation explicitly rejected as an unvalidated behavior change.

### Rollback

The refactor lands as five sequential squash-merge commits (Phase A → B → C → D → E). `git revert <phase-N-sha>` reverts a single phase; full rollback reverts E, D, C, B, A in that order. Added directories (`/common/`, `<skill>/scripts/_common/`, `quorum-review/scripts/quorum/`) are removed by the respective phase reverts. The shim contract preserves test imports throughout; if a regression is found post-merge, the test suite is the proof gate.

## v3.0 → v3 (March 2026)

See git history. v3 introduced anchor-aware ledger, conservative merge pipeline, independent verifier, mode split (plan/spec/code), and code anchors.

## v2.x

See git history. v2 introduced structured review parsing, canonical issue IDs, anonymous deliberation, issue-level consensus, cross-critique, context compression, failure-policy options, and the supermajority default.
