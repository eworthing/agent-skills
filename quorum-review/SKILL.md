---
name: quorum-review
description: >
  Multi-provider consensus review system (v3.1). Orchestrates anonymous
  quorum reviews for plans, specs, and code diffs across reviewers from
  different providers (Claude, Codex, Copilot, Antigravity/agy, Gemini),
  tracks canonical
  issue IDs in a shared ledger, merges only semantically equivalent
  issues, and derives the final verdict from surviving blockers — not
  raw vote counts — with an independent external verifier. Use when a
  single reviewer's verdict feels unreliable, when you need defensible
  blocker IDs for audit, when planning high-stakes changes (security,
  migrations, architecture), or when the user asks for "panel review",
  "consensus review", "multi-model review", "quorum review", or a
  "second opinion across AI providers".
argument-hint: "<artifact-file> [--reviewers claude:sonnet,codex,agy] [--mode plan|spec|code] [--threshold unanimous|super|majority] [--verifier provider:model] [--skip-verification]"
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
---

# Quorum Review — Multi-Provider Consensus (v3.1)

## Contents

- [Bundled resources](#bundled-resources)
- [What it does](#what-it-does)
- [Invocation](#invocation)
- [Modes](#modes)
- [Round flow](#round-flow)
- [Role packs](#role-packs)
- [Temp files](#temp-files)
- [Examples](#examples)
- [What changed in v3.1](#what-changed-in-v31)
- [Migration notes from v2.4](#migration-notes-from-v24)

## Bundled resources

Read on demand based on what you need:

- [`references/protocol.md`](references/protocol.md) — **authoritative machine contracts**: ledger JSON schema, merge classification rules, verifier I/O contract, accepted anchor keys, v2 → v3 alias migration. Source of truth for what `run_quorum.py` accepts and emits.
- [`references/output-format.md`](references/output-format.md) — reviewer output template (round 1 + round 2+ cross-critique), per-issue confidence requirements, code-anchor requirements, blind-mode formatting. Include in every reviewer prompt.
- [`references/claude-code.md`](references/claude-code.md), [`references/codex.md`](references/codex.md), [`references/copilot.md`](references/copilot.md), [`references/antigravity.md`](references/antigravity.md) (`agy` — experimental, not read-only), [`references/gemini.md`](references/gemini.md) (EOL 2026-06-18; enterprise-only, successor is `agy`) — per-provider CLI cheatsheets.
- [`references/env.md`](references/env.md) — environment variables the orchestrator + adapter read (`CODEX_HOME`, `GEMINI_CONFIG_DIR`, `QUORUM_PARSE_FAILURES_LOG`, etc.).
- Run [`scripts/run_quorum.py`](scripts/run_quorum.py) — the orchestrator (compatibility shim; see [`scripts/quorum/`](scripts/quorum/) for the implementation).
- See [`scripts/run_review.py`](scripts/run_review.py) — per-reviewer adapter invoked by the orchestrator (vendored `_common/` for provider dispatch).
- [`scripts/_common/`](scripts/_common/) — vendored copy of the shared infrastructure in `/common/` at the repo root. **Do not edit** — re-sync via `python3 common/scripts/sync_common.py`.

## What it does

- Launches multiple reviewer CLIs via `run_review.py`
- Keeps reviewer identities anonymous in shared context (`Reviewer A/B/C`)
- Tracks canonical blocking and non-blocking issue IDs in a ledger
- Merges only semantically equivalent issues; related/distinct and conflicts stay as relations only
- Verifies surviving blockers with an external verifier outside the panel
- Derives the final verdict from the ledger, not from reviewer tallies

The host agent revises the artifact between rounds; the orchestrator does not edit the artifact itself.

## Invocation

```bash
python3 scripts/run_quorum.py \
  --reviewers "claude:sonnet,gemini:pro,codex" \
  --plan-file <artifact-file> \
  --quorum-id <id> \
  --round 1 \
  [--mode plan|spec|code] \
  [--threshold unanimous|super|majority] \
  [--on-failure fail-closed|fail-open|shrink-quorum] \
  [--verifier provider:model] \
  [--max-rounds 5] \
  [--skip-verification] \
  [--sequential]
```

Notes:

- `--plan-file` is the artifact input path. In `code` mode, point it at a code diff or patch file.
- `--mode` defaults to `plan`; `spec` uses the same panel path as `plan`.
- `--verifier` must be an external provider:model pair. If omitted, the orchestrator auto-selects a verifier outside the panel.
- `--threshold` controls how many supporters a blocker needs to survive. Prefer:
  - `unanimous` — when false-positive blockers are very expensive (e.g., a release-gating review) and you want every reviewer to back each blocker before it can REVISE the artifact.
  - `super` (default) — for most reviews; tolerates one dissenting reviewer (N-1 of N) so a single confused reviewer cannot suppress a real blocker.
  - `majority` — for fast-moving iterative drafting where you want blockers to surface easily and the host agent will adjudicate.
- `--max-rounds` has a hard cap of 5. At round 5 the orchestrator forces a final verdict regardless of convergence.
- `--skip-verification` bypasses the independent verifier stage. Use this when you want faster turnaround and trust the panel's consensus without external validation (e.g., during iterative drafting).

## Modes

| Mode | Purpose | Prompt flavor |
|------|---------|---------------|
| `plan` | Default plan review | Plan/spec contract |
| `spec` | Backward-compatible alias for plan-style review | Plan/spec contract |
| `code` | Review a code diff/change | Code contract with file/line or hunk anchors |

## Round flow

1. **Round 1** — independent parallel review.
2. **Ledger build** — canonical IDs are assigned and issue metadata is stored.
3. **Merge** — only equivalent issues merge; related/distinct and conflicts are recorded as relations only.
4. **Rounds 2+** — anonymous cross-critique with compressed later rounds and blind mode.
5. **Verification** — surviving blockers are checked by an external verifier.
6. **Verdict** — APPROVED or REVISE is derived from surviving blocking issues.

Round 1 verdicts are based on the raw independent ledger; merge results are persisted for later rounds.

For the full per-section reviewer output contract, see `references/output-format.md`. For the ledger JSON shape, merge classification rules, anchor key set, and verifier I/O contract, see `references/protocol.md`.

## Role packs

Reviewer prompts inject hidden role labels to sharpen each reviewer's focus. Labels never appear in shared deliberation context (anonymity invariant).

- `plan` / `spec`: Skeptic, Constraint Guardian, User Advocate, Integrator-minded reviewer
- `code`: Correctness reviewer, Security reviewer, Maintainability reviewer, Performance/operability reviewer

## Temp files

The orchestrator writes reviewer prompts, reviews, session metadata, the merged ledger, deliberation context, tally JSON, and merge logs under the configured `--tmpdir`. The ledger lives at `qr-${QUORUM_ID}-ledger.json` and the merge log at `qr-${QUORUM_ID}-merge-log.jsonl`. Parse-failure telemetry (when a reviewer's output cannot be parsed strictly) lives at `qr-${QUORUM_ID}-parse-failures.jsonl`.

**Codex isolation + cleanup.** The panel fans out reviewers in parallel, so each Codex reviewer (and the verifier) runs in its own isolated `CODEX_HOME` — otherwise concurrent Codex runs would share `~/.codex/sessions/` and capture each other's sessions. Each per-run home is recorded in `qr-${QUORUM_ID}-codex-homes.list`. After the **final** round of a review (approved, indeterminate, or round-limit), reclaim them:

```bash
python3 scripts/qr_paths.py --cleanup --id-prefix "qr-${QUORUM_ID}"
```

It validates every recorded home before removing it and is safe to re-run. Do **not** run it between rounds — round 2+ resumes the homes created in round 1.

## Examples

Plan review:

```bash
python3 scripts/run_quorum.py \
  --reviewers "claude:sonnet,gemini:pro,codex" \
  --plan-file /tmp/plan.md \
  --quorum-id demo1 \
  --round 1 \
  --mode plan
```

Code review with an external verifier:

```bash
python3 scripts/run_quorum.py \
  --reviewers "claude:sonnet,gemini:flash,codex" \
  --plan-file /tmp/change.patch \
  --quorum-id demo2 \
  --round 1 \
  --mode code \
  --verifier copilot:gpt-5.4
```

## What changed in v3.1

Internal refactor; CLI, ledger schema, verdict semantics, and merge classifications are unchanged. Highlights below; full detail in git history.

- `scripts/run_review.py` migrated to the vendored `scripts/_common/` package (provider/metadata/session/process/log helpers shared with peer-plan-review).
- `scripts/run_quorum.py` is now a compatibility shim; the implementation lives in `scripts/quorum/` (cli, orchestrator, ledger, parsing, merge, verification, prompts).
- Reviewer output parsing hardened: strict Tier-1 contract plus an explicit Tier-2 variant matcher (whitespace, case, trailing punctuation). No keyword-heuristic tier. Parse failures emit telemetry to `parse-failures.jsonl` for operator audit.
- Provider allow-list (`ACCEPTED_REVIEWERS`) keeps opencode (present in the shared `PROVIDERS` registry) out of every quorum-review CLI surface.

## Migration notes from v2.4

- Plan/spec review still works, but `spec` is now a first-class mode alias.
- Code review uses anchors for file/line or diff hunk references.
- Verification is independent from the review panel.
- Merge handling is conservative: only equivalent issues merge; related issues stay linked.
- Invalidated blockers no longer drive a REVISE verdict.
