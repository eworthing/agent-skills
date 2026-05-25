# Source-Verification Prompt — MERGED INTO REVIEW-PROMPT.md (2026-05-25)

**This file is intentionally short.** Per user directive 2026-05-25, the source-veracity review prompt has been merged into the single peer-review prompt at:

→ [`REVIEW-PROMPT.md`](REVIEW-PROMPT.md)

REVIEW-PROMPT.md now covers both review axes that used to be split:

1. **Internal consistency** — claim-overstating, schema composability, adoption-order, "contest-refactor wins" overclaim, missed competitors, missed mechanisms (original REVIEW-PROMPT scope)
2. **Source veracity** — does each gap-doc claim about competitor source AND about contest-refactor's own source survive filesystem inspection? Paraphrase drift, fabricated details, wrong line numbers (former SOURCE-VERIFICATION-PROMPT scope)

The merged prompt adds:

- **Class 6** external-research-claim verification (validates SOURCE-STATUS.md inversion log entries)
- **Class 9** user-directive consistency (archgate-prereq + methods-focus directives propagated correctly)
- **High-value spot-checks for 2026-05-25 newly-added claims** (archgate, continuous-claude-v3, Bouncer, pauhu, TimmyZinin, fastruby, alirezarezvani, wshobson, VoltAgent)
- **Schema_version 5 composability check** (Gap E in CROSS-MODEL-CRITIC + Gap F in HALT-STATE both bump 4→5)

This stub file is preserved to:

- Maintain git-history traceability of the merge
- Catch external bookmarks / URLs / scripts that still reference this path
- Document the consolidation decision for future readers

If you arrived here looking for the source-verification prompt: use REVIEW-PROMPT.md.
