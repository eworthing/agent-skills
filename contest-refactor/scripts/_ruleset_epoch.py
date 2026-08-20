"""_ruleset_epoch.py — the ruleset-epoch classifier (backlog item [I1]).

G43 (2026-08-06, commit 9346822) and G46 (2026-08-18, commit 9528774) both added
REQUIRED v4 fields with no schema bump and no default-fill table — the pattern
output-format-migrations.md itself forbids by example (the v2->v3 bump did both).
The result: this skill's own dogfood artifact (`CURRENT_REVIEW.json` at the repo
root, loop 15, HALT_LOOP_CAP, committed 2026-08-05 — a full day before G43 existed
and 13 days before G46) fails `validate-artifact.py --mode strict` on fields that
did not exist when it was written. Rules cannot retroactively invalidate artifacts
they postdate.

output-format-migrations.md already names the fix for exactly this shape: "Scope
the gate to artifacts written at or after the ruleset that introduced it, read
from `skill_rev` (G19) — which is why that field exists." This module is that
scoping mechanism, extracted once so every epoch-gated checker shares one
definition instead of repeating an inline `if` (the mistake that created G43/G46's
defect in the first place).

## Why two epochs, not one per gate

`skill_rev` — "git -C $SKILL_DIR rev-parse --short HEAD", captured in Step -1,
schema_version >= 4 — is the ONLY field naming which ruleset produced an artifact
(startup.md, output-format-json.md:204). It was introduced at commit f94d802
(2026-08-06 08:44), ~25 minutes before G43 and 12 days before G46. G19's own
docstring (_artifact_history.py:307) already states the load-bearing fact this
classifier is built on: a validator "cannot tell 'this version omitted it' from
'this run predates the field', so presence is a Step -1 emit obligation, not a
validation-time inference." That statement rules out reconstructing fine-grained
epochs (e.g. "at-or-after 9346822 but before 9528774") from the field's content:
a git short SHA carries no timestamp, and ordering two arbitrary SHAs requires a
live git repository containing both commits — unavailable for a fixture's
synthetic skill_rev, unavailable for an artifact from a different clone's history,
and actively wrong to depend on inside a selftest that must run standalone.

So the classifier draws exactly the one boundary the evidence supports: does this
artifact carry proof it was emitted by a loop that already attested to its own
ruleset, or not. `skill_rev` present and syntactically valid -> CURRENT.
Anything else (null, absent, empty, malformed) -> LEGACY. Every requirement in
REQUIREMENT_EPOCHS below currently keys to CURRENT because every one of them
(G43, G46, and the future clients named in the [I1] task — independence/
transitions/rounds/G29 version equality/G17) postdates skill_rev's own
introduction. The table exists so the SET of epoch-gated requirements is one
place to read and one place to extend, not so today's epoch space has more than
two members; a genuinely later boundary (e.g. a v5-only requirement) gets a third
EPOCHS entry when one is actually needed, per output-format-migrations.md's
"epoch entry in the matrix" clause.

## Fail-closed direction

This module backs RETROACTIVE requirements only — a rule whose fields were added
after artifacts already existed on disk (G43, G46). For those, an artifact that
cannot be PROVEN current is classified legacy, never the reverse: a marker-less
artifact goes unchecked rather than a genuinely-legacy artifact being wrongly
failed. That is an intentional, asymmetric trade — the cost lands as under-
coverage on artifacts that omit `skill_rev` (including every fixture and selftest
artifact in this corpus today; none carry one — see the [I1] report), not as a
false failure on real committed history. Closing that gap is an EMITTER
obligation (skill_rev capture is already mandatory at schema_version >= 4,
startup.md Step -1), not something this validator-side classifier can compel:
G19 checks skill_rev's TYPE when present, deliberately not its presence, for the
same reason this module cannot infer presence from absence either.

A GO-FORWARD requirement (one an emitter is newly obligated to satisfy, as
opposed to a retroactive one judging artifacts already on disk) is a different
problem this module does not solve: the matrix only decides whether an existing
required field applies to a given artifact, and documents in
output-format-migrations.md that new-current-skill emission is a prose emitter
obligation, not something the classifier enforces going forward either.
"""

from __future__ import annotations

import re

LEGACY = "legacy"
CURRENT = "current"

# Oldest -> newest. Index comparison in `applies()` is what lets a future third
# epoch slot in without changing any call site.
EPOCHS: tuple[str, ...] = (LEGACY, CURRENT)

# A short git SHA per `git rev-parse --short HEAD`: lowercase hex, default
# abbrev 7, up to the full 40. Matches G19's own acceptance (_artifact_history.py
# check_g19_provider_model treats skill_rev as "non-empty string or null" at the
# type level; this is the additional shape check that makes a value usable as an
# epoch marker instead of an opaque unverified string).
_SKILL_REV_RE = re.compile(r"^[0-9a-f]{4,40}$")

# The compatibility matrix: DATA, not scattered `if`s. Maps a versioned
# requirement to the epoch at-or-after which it applies. A requirement absent
# from this table is NOT epoch-gated — it is unconditional at whatever
# schema_version floor its own checker already applies (e.g. G19's type check,
# which is deliberately not epoch-scoped: it never requires presence).
#
# Add a new required field or record here — never as an inline epoch `if` in the
# checker — per output-format-migrations.md's "Adding a required field" rule.
REQUIREMENT_EPOCHS: dict[str, str] = {
    # G43: convergence_pass[] coverage + clean-streak proposal owing.
    # Landed 2026-08-06, commit 9346822.
    "G43_CONVERGENCE_PASS": CURRENT,
    # G46: loop_result.finding_family / effort / repair_revalidation.
    # Landed 2026-08-18, commit 9528774.
    "G46_REMEDIATION_FIELDS": CURRENT,
    # Slots for future clients named in the [I1] task. Each ships as an entry
    # here, not a new inline check, the day its checker starts requiring the
    # field unconditionally. Until then these fields stay optional-with-shape-
    # gating (the G19 precedent; see _artifact_independence.py's docstring for
    # why that route was chosen there instead) or report-only.
    # "INDEPENDENCE_ISOLATION_FIELDS": CURRENT,
    # "TRANSITIONS_REQUIRED_FIELDS": CURRENT,
    # "ROUNDS_REQUIRED_FIELDS": CURRENT,
    # "G29_VERSION_EQUALITY": CURRENT,
    # "G17_COVERAGE_CITATION": CURRENT,
}


def classify(current_review: dict, history: dict | None = None) -> str:
    """Return the ruleset epoch `current_review` was produced under.

    `history` (REVIEW_HISTORY.json, when available) is accepted for interface
    symmetry with the checkers this feeds (G43 already threads history through)
    and for a future signal — e.g. cross-loop skill_rev consistency — but is not
    read today: classification is a pure function of `current_review["skill_rev"]`.
    See the module docstring for why a coarser, two-epoch boundary is what the
    evidence supports rather than a per-commit ordering.
    """
    skill_rev = current_review.get("skill_rev")
    if isinstance(skill_rev, str) and _SKILL_REV_RE.match(skill_rev):
        return CURRENT
    return LEGACY


def applies(requirement: str, current_review: dict, history: dict | None = None) -> bool:
    """True when `requirement` (a REQUIREMENT_EPOCHS key) is owed on this artifact.

    A requirement not in REQUIREMENT_EPOCHS is unconditionally owed (True) — it
    is not epoch-gated at all, so this function only ever narrows a checker's
    floor, never broadens it.
    """
    required_epoch = REQUIREMENT_EPOCHS.get(requirement)
    if required_epoch is None:
        return True
    return EPOCHS.index(classify(current_review, history)) >= EPOCHS.index(required_epoch)
