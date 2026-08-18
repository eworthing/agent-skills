# Item 1 — Retrospective Credential History Audit (2026-08-17)

## Verdict: CLEAN — 0 true hits

No credential-shaped value that isn't a documented fixture fake was ever found
in this repository's git history, across all reachable branches/tags, all
dangling/unreachable objects still present in the object database, and the
current working tree.

## Scope

G44 (`contest-refactor/scripts/_artifact_credentials.py`) is a forward-looking
mechanical backstop: it scans the loop's five persistence sinks
(`CURRENT_REVIEW.md`, `CURRENT_REVIEW.json`, `REVIEW_HISTORY.md`,
`REVIEW_HISTORY.json`, `findings_registry.json`) as they exist on disk today.
This audit is the one-time retrospective half: did any past dogfood run of
the contest-refactor loop already commit a credential-shaped value into this
repo's history — including copies later deleted from the working tree — before
G44 existed to catch it?

In scope for the inventory: the five sink filenames above, any `*.quarantine`
file, `LOOP_STATE.json`, and any other loop event/log artifact. Per
`contest-refactor/references/output-format.md` § "## Artifacts", the loop's
full persistence contract is exactly these six filenames — there is no
separate "loop event/log" artifact type, so nothing beyond the six was
missed by omission.

## Method

All commands run from the repo root, read-only, no repo state changed.

1. **Enumerate every sink-shaped blob ever reachable from any ref** (all
   branches, remote-tracking refs, and tags):
   ```
   git rev-list --objects --all
   ```
   filtered to lines whose path matches
   `(^|/)(CURRENT_REVIEW\.(md|json)|REVIEW_HISTORY\.(md|json)|findings_registry\.json|LOOP_STATE\.json)$|\.quarantine$`.
   This yielded 500 unique blob objects across 323 distinct historical paths.

2. **Enumerate the same from dangling/unreachable objects** (WIP snapshots,
   amended-away commits, orphaned branch work still sitting in the object
   database but not reachable from any ref):
   ```
   git fsck --full --unreachable --dangling
   ```
   → 42 dangling commits, 142 dangling trees. Each was tree-walked
   (`git ls-tree -r <sha>`) and filtered the same way. This added 9 blob
   contents not already covered by step 1 (509 unique blobs total across
   both steps). `git stash list` was also checked — empty, nothing to add.

3. **Swept the current working tree** (`find . -not -path './.git/*'`) for
   the same filenames anywhere in the repo, including scratch/analysis
   directories — to catch anything present now that predates G44's own
   scan being wired into the loop.

4. **Scanned every one of the 509 unique historical blobs** by reading its
   content via `git cat-file -p <sha>` and running it through the shipped
   scanner directly — no logic was replicated. The module's `_scan_line(text)`
   function operates on a plain string (not a file path), which fit the
   streaming/blob-content use case exactly:
   ```python
   import sys; sys.path.insert(0, "contest-refactor/scripts")
   import _artifact_credentials as ac
   ac._scan_line(line_text)
   ```
   This applies the full shipped pattern table (`_CREDENTIAL_PATTERNS`: AWS
   access key ID, AWS secret access key proximity heuristic, `sk-` API key,
   GitHub PAT/OAuth token, Slack bot/user token, PEM private-key header,
   generic `api_key=` shape) plus both shipped transform detectors (base64
   decode-then-match, and `"a" + "b"` concat-split-then-match) — unmodified.

5. **Defense-in-depth sanity pass beyond G44's precise patterns**: a second,
   deliberately loose keyword scan (plain case-insensitive substring match
   on `AKIA`, `sk-`, `ghp_`, `gho_`, `ghs_`, `xoxb-`/`xoxp-`/`xoxa-`, PEM
   `BEGIN ...` headers, and generic `password`/`secret`/`token=`/`bearer`/
   `authorization:` keywords) across the same 509 blobs, to catch anything
   the precise, low-false-positive-by-design regexes might structurally
   miss. Every loose hit was individually triaged (method below) — nothing
   in this pass ever had its matched text printed to any output.

Every triage step below reports blob sha, historical path, commit
reference, line number, credential TYPE, and pattern name only — the
matched value or any substring of it is never reproduced in this document
or was ever printed to a terminal/log during the audit, per G44's own
diagnostics rule.

## Inventory

| Category | Unique blobs | Status |
|---|---|---|
| `CURRENT_REVIEW.md` | 65 | scanned |
| `CURRENT_REVIEW.json` | 182 | scanned |
| `REVIEW_HISTORY.md` | 52 | scanned |
| `REVIEW_HISTORY.json` | 168 | scanned |
| `findings_registry.json` | 36 | scanned |
| `LOOP_STATE.json` | 6 | scanned |
| `*.quarantine` | 0 | none ever existed in history |
| **Total unique blob contents** | **509** | **all scanned** |

Two distinct origins for these 509 blobs:

**A. Real dogfood run — `peer-plan-review/` (5 sink files, 37 blob
revisions, all clean).** The contest-refactor loop was run against its own
`peer-plan-review` skill for 7 loops between 2026-06-22 and 2026-06-29
(commits `c1804f4` through `9038230`). Each loop committed updated copies of
all five sinks directly at `peer-plan-review/CURRENT_REVIEW.{md,json}`,
`peer-plan-review/REVIEW_HISTORY.{md,json}`, and
`peer-plan-review/findings_registry.json` (plus two registry-only backfill
commits `cabed62` and `28e06bc`). Commit `9038230` (2026-06-29,
"chore(peer-plan-review): drop leaked contest-refactor artifacts + design
doc; guard .gitignore") deleted all five from the working tree and added
them to `.gitignore` — confirmed present at repo-root `.gitignore` lines
14–18 — so this was already recognized and remediated as a process leak at
the time, but the content remains reachable in git history, which is
exactly the retrospective gap this audit closes. **All 37 blob revisions
across these 5 files scanned clean under the precise G44 pattern set.**

**B. Eval fixtures — `contest-refactor/evals/**` (318 historical paths,
472 blobs, including the 9 dangling-only blobs).** Synthetic fixture data
for exercising 60+ validation gates (`artifact-smoke/*`, `fixtures/*`
including `handoff-*`, `loop-state-*`, `missing-state-*`, `g44-credential-*`,
etc.). Only five of these fixture directories are the credential-specific
family, and they are the intentionally-planted positive/negative cases for
G44 itself:

- `contest-refactor/evals/fixtures/g44-credential-akia-plain/`
- `contest-refactor/evals/fixtures/g44-credential-base64/`
- `contest-refactor/evals/fixtures/g44-credential-concat-split/`
- `contest-refactor/evals/fixtures/g44-credential-direct-write-bypass/`
- `contest-refactor/evals/fixtures/g44-credential-type-only-restraint/`

The current working-tree sweep found the same 318 fixture-family paths
present on disk today (nothing hidden that isn't already tracked), plus the
same peer-plan-review-shaped absence confirmed above (the five files do
**not** exist in the current `peer-plan-review/` working tree — only in
history).

## Findings

### Expected fixture fakes (11 precise-pattern hits, all accounted for)

Every hit from the shipped `_CREDENTIAL_PATTERNS` scan is inside the
documented `g44-credential-*` fixture family, per each fixture's
`fixture.toml`: `contest-refactor/evals/fixtures/g44-credential-akia-plain/fixture.toml`
states the fixture uses "AWS's own documented example key
`AKIAIOSFODNN7EXAMPLE`" (a publicly known, non-secret placeholder used
throughout AWS's own documentation and open-source tooling — safe to name
verbatim). The 11 hits break down as:

| Fixture | Sink | Line | Type | Transform |
|---|---|---|---|---|
| g44-credential-akia-plain | CURRENT_REVIEW.json | 126 | AWS access key ID | plain |
| g44-credential-akia-plain | CURRENT_REVIEW.md | 9 | AWS access key ID | plain |
| g44-credential-akia-plain | REVIEW_HISTORY.json | 128 | AWS access key ID | plain |
| g44-credential-base64 | CURRENT_REVIEW.json | 126 | AWS access key ID | base64 |
| g44-credential-base64 | CURRENT_REVIEW.md | 9 | AWS access key ID | base64 |
| g44-credential-base64 | REVIEW_HISTORY.json | 128 | AWS access key ID | base64 |
| g44-credential-concat-split | CURRENT_REVIEW.json | 126 | AWS access key ID | concat-split |
| g44-credential-concat-split | CURRENT_REVIEW.md | 9 | AWS access key ID | concat-split |
| g44-credential-concat-split | REVIEW_HISTORY.json | 128 | AWS access key ID | concat-split |
| g44-credential-direct-write-bypass | REVIEW_HISTORY.json | 140 | AWS access key ID | plain |
| g44-credential-direct-write-bypass | REVIEW_HISTORY.md | 2 | AWS access key ID | plain |

`g44-credential-type-only-restraint` produced no hits — consistent with it
being the negative/restraint fixture (tests that G44 does *not* fire on
credential-adjacent-but-not-credential-shaped content). This same 11-hit set
was reproduced identically when re-scanning the merged reachable +
dangling-object blob corpus (509 blobs) — the dangling-only 9 blobs added no
new hits, they are duplicate/superset fixture content from WIP branch
snapshots (e.g. `codex/contest-refactor-advisory-audits`).

### True hits: none

Zero hits outside the `g44-credential-*` fixture family, in either the
precise-pattern scan or the broader defense-in-depth keyword pass, with one
set of loose-pass matches that required manual triage:

**Loose "AKIA" matches (8):** all map to blob shas already in the 11-hit
table above — no new content.

**Loose "sk-" matches (16, all inside the real `peer-plan-review/` dogfood
blobs, 6 distinct blobs, 2 occurrences each):** the precise pattern
`\bsk-[A-Za-z0-9]{20,}\b` correctly did not match any of these. Structural
triage (character class immediately preceding "sk-", and the length of the
alnum run immediately following it — never the actual characters) confirmed
every one of the 16 occurrences has a **word character directly before
"sk-"** (i.e. "sk-" is a substring inside a longer word, not a token at a
word boundary) and an **identical fixed-length alnum run after it across all
16 occurrences**, consistent with a single recurring English compound word
in review prose (e.g. a hyphenated adjective used repeatedly across these
review documents), not a credential token. No PEM headers, GitHub/Slack
token prefixes, or `password`/`secret`/`token=`/`bearer`/`authorization:`
keywords matched anywhere in the 509-blob corpus.

`LOOP_STATE.json` (6 unique blobs, all under eval fixtures) scanned clean,
consistent with G44's own documented rationale for excluding it from its
live scan: its `evidence` field structurally carries only `[start, end]`
line-number pairs plus a SHA-256 hash, never quoted text.

## Disposition

**No rotation action needed.** There are no true hits — nothing
credential-shaped exists in this repository's history (reachable or
dangling) outside the documented, intentionally-fake `g44-credential-*`
fixture family, which uses AWS's own public non-secret example key and is
expected to remain exactly where it is as G44's regression corpus.

The `peer-plan-review/` dogfood leak (2026-06-22 → 2026-06-29) was already
remediated at the working-tree level by commit `9038230` (deletion +
`.gitignore` guard) before this audit ran, and this audit confirms that leak
never carried a credential-shaped value in the first place — so there is
nothing to rotate and no security exposure from that incident. The content
still exists in git history (that's inherent to git; deleting a file doesn't
remove its blob from history) but since it was clean content, that's a
non-issue.

If a future retrospective audit of this kind *does* find a true hit, the
standing guidance (per the shipped G44 plan) is: rotate the specific
credential type identified (AWS key → rotate via IAM; API secret key →
regenerate at the provider; GitHub/Slack token → revoke and reissue) using
only the TYPE/sink/line reported, never a value copied from this report,
and treat rewriting git history to purge the blob as a **separate,
explicitly-authorized decision** — not something this audit performs or
recommends unilaterally, since history rewriting affects every clone and
collaborator of this repository.

## Confidentiality confirmation

This report contains no matched credential value, decoded base64 payload,
or concatenated string fragment from any scanned blob, and no such value
was printed to any terminal, log, or intermediate file during this audit —
every diagnostic (precise-pattern hits, loose keyword hits, and the "sk-"
structural triage) was built entirely from constants (blob sha, path,
commit, line number, pattern/keyword name, character-class/length
classification), consistent with G44's own diagnostics rule.
