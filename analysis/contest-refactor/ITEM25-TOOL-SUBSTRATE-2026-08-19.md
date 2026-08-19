# Item 25 — Tool-Grounded Substrate + Per-Language Rules: Inventory + Design Note (2026-08-19)

Item 25 is unblocked as of `ae272ec` — items 1, 3, and 18 are all in place
(`ITEM3-HARD-RULE-PROPAGATION-2026-08-19.md`). Tranche 5 requires a design note before code, and
requires the item to split into "a bounded tool runner … and per-language rule packs, scoped
initially to the two or three languages the eval corpus actually exercises" (`deep-dive:1237`).

## Verdict: split it. One half is buildable and nearly free; the other is budget-blocked.

> **Status 2026-08-19:** Half A (slices A1–A4) is **shipped** — `scripts/tool_runner.py`,
> `scripts/_tool_runner_selftest.py`, and Step-0 sub-step 6c, at **zero loop-path token cost**
> (budget unchanged at 84,115/84,200). Half B remains blocked on the §7 budget decision.

- **Half A — the bounded tool runner.** Buildable now, and it belongs in **Step 0 (main agent)**,
  not in the loop. That placement costs **zero loop-path tokens** and gives *better* isolation than
  running tools in-loop, because raw analyzer output never crosses the subagent boundary at all.
- **Half B — per-language rule packs.** **Budget-blocked.** The two upstream packs matching our
  corpus total **3,029 tokens** (`swift.md` 1,422 + `python.md` 1,607) against **85 tokens** of
  per-loop headroom. This needs a displacement or ceiling decision made deliberately, not smuggled
  in as a side effect of an implementation.

## 1. Inventory — the substrate already exists

The backlog row's premise is *"Our Critic generates findings with no deterministic analyzer output
in the loop"* (`deep-dive:1003`). **That is false as written.** Nine first-party deterministic tools
ship, and eight are reachable from skill prose:

| Tool | Invoked from | Role |
|---|---|---|
| `audit_boundaries.py` | `method.md:82` | circular first-party import cycles |
| `repo_map.py` | `method.md:46, 82` | import graph, fan-in/out, public surface; **auto-engages >300 files** |
| `audit_clones.py` | `method.md:85` | near-duplicate function bodies |
| `audit-public-surface.sh` | `method.md:85` | `public` decls with no cross-module caller |
| `audit-naming.sh` | `method.md:85` | fuzzy-name clusters |
| `audit-enum-interpretation.sh` | `method.md:85` | domain enums interpreted outside their home |
| `audit-churn.sh` | `startup.md` | churn heatmap → `churn_top20` |
| `audit_metric_trend.py` | `method.md:36` | cross-loop metric regression |
| `audit_cochange.py` | **nowhere** | change-coupled, structurally distant files |

Beyond the tools, the doctrine Gap 23 proposes importing is **largely already shipped**:

- **"A lead, not a finding"** (Sentry's contribution) — we ship it as `promotion_allowed: false` on
  every tool output, with the Critic required to re-derive any judgment.
- **The context rule** ("tool output to a file, summarize counts — never dump raw output into
  context") — present for `repo_map.py`, which is explicitly *"ephemeral"* and *"NEVER persisted"*.
- **Meta-Rule 1** — *"Metrics support judgment; they never decide it. Tool output (SwiftLint,
  Taylor, xccov, TSAN, compiler diagnostics, grep counts) is evidence to investigate. Not a verdict.
  Every metric-backed finding must trace metric → source → behavior."*
- **A mandatory mechanical grep** at `method.md:85` — `rg -nE "LEGACY|TEMPORARY|DEPRECATED|DO NOT|
  ASPIRATIONAL|carve-out|SHIM|FIXME|HACK|TODO"` — with every hit required to be verified against
  current code.
- **A tool-gated score**: `simplicity >= 9` requires the mechanical-seed outputs
  (`audit-enum-interpretation.sh`, `audit_clones.py`) to be *adopted or falsified* in Builder Notes.

## 2. The genuine delta

Four things, and only four:

1. **No cost ordering and no interrupt rule.** The tools are invoked where they are topically
   relevant, not cheapest-first, and nothing says "if a fast tool surfaces a critical hit, escalate
   immediately". tech-audit's contribution is the *ordering*, which we lack entirely.
2. **Every tool is one we wrote.** `rg` is the only third-party binary the skill invokes (8 sites).
   SwiftLint, Taylor, xccov and TSAN are *named as evidence sources* in Meta-Rule 1 but never run.
   **This is the actual item**: admitting third-party analyzers, which is precisely why the row
   inherits items 1/3/18's controls — a secret scanner's output contains the secrets it found.
3. **No version-conditioned rules.** Our lenses are stack lenses, not per-language packs, and
   nothing expresses "Go 1.22 loopvar"-class facts.
4. **No anti-duplication mandate** — see §3, where it turns out to be less of a gap than it looks.

**Orphan found:** `audit_cochange.py` ships with a selftest (`_audit_cochange_selftest.py`) and is
invoked by no prose in `SKILL.md` or `references/`. It is dead capability — either wire it into
`method.md` Step 3's coupling cross-check, where change-coupling is topically exact, or retire it.
Not fixed here; it is a one-line prose decision that belongs to whoever builds Half A.

## 3. The tension that isn't

alibaba's anti-duplication mandate looks like it contradicts Meta-Rule 1. Read verbatim, it does
not. From `refs/competitors/contest-refactor/alibaba-open-code-review/internal/config/rules/rule_docs/go.md:4`:

> Do not duplicate findings that `go vet`, Staticcheck, `go test -race`, the compiler, or `gofmt`
> can determine reliably **unless the diff shows a concrete user-visible consequence those tools
> will not express.**

The escape clause is the whole rule. It says: *do not restate a tool's output as a finding unless
you add the consequence the tool cannot express.* Meta-Rule 1 says: *every metric-backed finding
must trace metric → source → behavior.* **These are the same rule from opposite ends**, and ours is
arguably the stronger form, because it demands the trace affirmatively rather than forbidding its
absence. The swift.md variant names our exact toolchain:

> Do not duplicate compiler, SwiftLint, or Xcode analyzer findings unless the diff creates concrete
> correctness impact.

**Design consequence:** do not port the anti-duplication mandate as a new rule. Port the *tool
names* into Meta-Rule 1's existing parenthetical when a tool is actually wired, so the rule keeps
naming the tools the loop really runs.

## 4. Where the ladder runs — Step 0, not the loop

**Run the tool ladder in Step 0, in the main agent, and pass only sanitized summaries into
`discovery`.** The Critic already reads `discovery` every loop (G40), so the findings-relevant
signal reaches it with no new loop-path prose.

Two independent reasons, and the second is the stronger one:

- **Token budget.** `startup.md` is main-agent-only and explicitly *"not part of the per-loop
  reload"*; empirically confirmed by the `--scope` fix (`ae272ec`), which added a full sentence to
  Step 0 and left the budget at 84,115/84,200 unchanged. In-loop placement in `method.md` (7,814
  tokens, per-loop) has 85 tokens of room, which is not enough for a ladder of any size.
- **Isolation.** Raw analyzer output is attacker-influenceable repository-derived text. Running
  tools in the main agent means that text is **never in the subagent's context at all** — only the
  sanitized summary crosses the boundary. Running the ladder in-loop would put raw tool output in
  front of the same agent that writes findings, which is the exposure items 1/3/18 exist to close.
  Step-0 placement is a stronger control than any prose rule about handling raw output would be.

## 5. Half A — the bounded tool-runner contract

One script, `scripts/tool_runner.py`, invoked from Step 0. Every outcome is typed; **no outcome is
silent**, because a tool that quietly did not run reads as a clean result.

| Outcome | Meaning | Recorded as |
|---|---|---|
| `ok` | ran, exit 0 or documented findings-exit | sanitized summary + counts + output digest |
| `absent` | binary not on PATH | `absent`, disclosed under coverage |
| `version_incompatible` | present but below the pinned floor | `version_incompatible` with observed + required |
| `timed_out` | exceeded its per-tool ceiling | `timed_out` with the ceiling; **partial output discarded** |
| `partial` | produced parseable output *and* a nonzero non-findings exit | counts recorded, marked `partial` |
| `skipped_no_redacted_mode` | fails closed per §6 | `skipped`, disclosed under coverage |

Two contract rules worth stating because they are the ones a later implementer will get wrong:

- **`absent` is not `clean`.** A coverage line must distinguish "gitleaks found nothing" from
  "gitleaks was not installed". Reporting the latter as the former is the survivor-metric hazard
  the tranche-3 work already named in a different setting.
- **`timed_out` discards partial output.** A truncated analyzer stream is not a smaller true
  result; it is an unknown fraction of one, and summarising it produces a count that reads as
  complete. Keep the fact of the timeout, drop the bytes.

The runner exits **0 always** — it reports, it does not gate. A tool's *findings* are candidate
evidence under `promotion_allowed: false` like every existing audit output.

## 6. The security boundary (items 1, 3, 18 inheritance)

Non-negotiable, from `deep-dive:1016`. Three controls, all of which have an existing counterpart
here rather than needing invention:

1. **Redacted modes, failing closed.** A tool with no redacted mode has its output sanitized before
   any use, or is skipped and disclosed. Our G44 credential-quarantine gate
   (`scripts/_artifact_credentials.py`) already scans persistence sinks for secret shapes and
   *"fails closed, never reproduces the value"* — the runner's sanitizer routes through it rather
   than growing a second implementation.
2. **No durable raw output.** Only sanitized summaries and output digests persist. `repo_map.py`'s
   ephemeral contract is the existing precedent to copy verbatim.
3. **Payload, not instruction.** Analyzer output is untrusted text under G14. Step-0 placement (§4)
   means it never reaches a dispatched agent, so this is enforced structurally rather than by prose.

Independent corroboration that the redaction control is the right shape — tech-audit reached the
identical rule from the opposite direction (`tech-audit-skill/DEVPLAN.md:254`):

> …about leaked secrets (gitleaks hits, hardcoded tokens) must reference the location only — never
> quote the secret value into the report or the findings.tsv (reports get committed/shared).

That is our redaction rule almost word for word, derived independently by a skill whose reports get
committed. RED fixtures must include analyzer output carrying **planted credentials** and
**injected instructions**, per the row's own requirement.

## 7. Half B — per-language packs, and the budget wall

The eval corpus exercises exactly two languages: **Swift** (103 files, 105 scenario references) and
**Python** (56 files). Upstream ships a matching pack for each, and they are good — precision
preamble, explicit negative clauses, version conditioning:

> **swift.md** — "Favor precision over recall: report only defects likely real in changed code and
> reachable execution paths. Prioritize crashes, data corruption, security issues, privacy issues,
> and concurrency bugs. Do not report style preferences."
>
> **pot.md**, as the clearest negative-clause example — "in a template (.pot) file every `msgstr` is
> expected to be empty; do not report empty `msgstr` entries as missing translations."

**They do not fit.** `swift.md` is 1,422 tokens and `python.md` is 1,607 — **3,029 combined against
85 tokens of headroom.** Three options, none of which should be chosen silently:

| Option | Cost | Note |
|---|---|---|
| Raise the ceiling | ~3k tokens on **every loop of every run** (~30k per 10-loop run) | The honest option if the packs prove their value; must be a measured decision, not a side effect |
| **Conditional load by detected stack** | Swift pack on the apple path only; Python pack on the generic path | **Corrected 2026-08-19.** The first draft said the Python pack "likely fits under today's ceiling" because generic counts ~4.1k fewer tokens than apple. That apparent slack was an artifact: the guard held **one** ceiling, measured on apple, and compared only `--lens` (default apple) against it, so generic growth was invisible until it crossed a number set for a different path. Fixed — each path now carries its own ceiling and one `--check` polices both: apple **84,115 / 84,200**, generic **80,037 / 80,100**. Real headroom on generic is **63 tokens**, not 4,163, so the Python pack (1,607) needs a deliberate generic bump to ~81,700 and the Swift pack (1,422) an apple bump to ~85,600. Both are now visible decisions rather than free lunches |
| Displace | edit `lens-apple.md` to make room | Real regression risk; needs its own measurement |

**Recommendation: neither pack ships without a measured reason.** A rule pack is judgment-shifting
prose, which is exactly the class this repo micro-tests against a no-guidance control before
shipping — and the last such micro-test cost ~3M tokens and was rejected. The detection value is
also unproven here specifically: the paired-arm study left the instrument saturated, so a pack's
incremental lift cannot currently be measured either way.

## 8. Slice contract

| Slice | Status | Acceptance as built | Cost |
|---|---|---|---|
| **A1. `tool_runner.py` + typed outcomes** | **SHIPPED** | `_tool_runner_selftest.py` asserts all six outcomes; **mutation-tested** — reintroducing counts on a timeout, keeping the raw message, or reporting `findings: 0` on `absent` each fail the suite | 245 LoC; **zero loop-path tokens** |
| **A2. Redaction + injection containment** | **SHIPPED** | planted `AKIA…` credential never reaches the summary (recorded by pattern type only, via G44's `_scan_line` — reused, not duplicated); injected instruction text counted as payload and never reproduced. Both verified by mutation: keeping the message trips all three security assertions at once | — |
| **A3. Wire a real tool** | **SHIPPED** | `ruff` wired with a `>= 0.15.0` floor and findings-exit `(0, 1)`. Live run against this skill returned `ok findings=2` — **and both were real defects in the selftest written minutes earlier** (two unused `noqa` directives), since fixed | 1 Step-0 sub-step (`startup.md` 6c) |
| **A4. Adopt or retire `audit_cochange.py`** | **SHIPPED — adopted** | wired into the same 6c sub-step rather than `method.md`: it mines git history, which is Step-0 work beside the churn list (6b), so it costs nothing on the loop path | — |
| **B. Per-language packs** | **BLOCKED** | the budget decision in §7 + a measurable lift | 3,029 tokens vs 85 |

## 9. Recommendation

**A1–A4 shipped 2026-08-19. B not built.** Half A is deterministic, testable, costs nothing on the loop path,
and closes the real gap the row names — that every tool in the loop is one we wrote. Half B is
3,029 tokens of judgment-shifting prose against 85 tokens of headroom, with no way to measure its
value on a saturated instrument. Recording the wall is the deliverable for B; the budget decision
belongs to the owner, not to an implementation detail.
