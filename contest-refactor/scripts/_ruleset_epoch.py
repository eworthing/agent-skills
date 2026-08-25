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

## Epoch boundaries

`skill_rev` — "git -C $SKILL_DIR rev-parse --short HEAD", captured in Step -1,
schema_version >= 4 — is the ONLY field naming which ruleset produced an artifact
(startup.md, output-format-json.md:204). It was introduced at commit f94d802
(2026-08-06 08:44), ~25 minutes before G43 and 12 days before G46. G19's own
docstring (_artifact_history.py:307) already states the load-bearing fact this
classifier is built on: a validator "cannot tell 'this version omitted it' from
'this run predates the field', so presence is a Step -1 emit obligation, not a
validation-time inference." That rules out guessing from an opaque or unresolved
SHA. The original LEGACY/CURRENT boundary therefore remains shape-based.

G49 was the first requirement with a later, provable boundary: commit 651ea50
introduced the hotspot-v2 handoff, so a live skill checkout can use Git ancestry
to classify that commit and descendants as HOTSPOT_V2. G32's fingerprint-binding
requirement (commit 44b4c03) is the second, same mechanism, and G50's hotspot-
triage requirement (commit 7ffd502) is the third, and G47's skip-reason
requirement (commit 1609cd6) is the fourth: `_is_at_or_after`
generalizes the ancestry + shallow-clone-fallback check, and `classify()` walks
`_PROVABLE_EPOCHS` newest-first so a new boundary slots in without touching the
older ones. A depth-1 clone falls back only when the artifact revision resolves
to that checkout's current HEAD — which proves at least the newest defined
epoch, since the fallback cannot tell which boundary it actually satisfied.
Unresolved revisions and copied non-Git skills remain at the older epoch rather
than being retroactively failed on a guess.

## Fail-closed direction

This module backs RETROACTIVE requirements only — rules whose fields were added
after artifacts already existed on disk (G43, G46, G49, G32's fingerprint
binding, G50). An artifact that cannot
be PROVEN to meet an epoch boundary stays in an older epoch: a marker-less or
unresolved artifact goes unchecked rather than a genuinely older artifact being
wrongly failed. That intentional asymmetric trade puts the cost on under-
coverage, not false failure of committed history. Closing the gap is an EMITTER
obligation (skill_rev capture is mandatory at schema_version >= 4, startup.md
Step -1), not a validator inference: G19 checks skill_rev's TYPE when present,
deliberately not its presence.

A GO-FORWARD requirement (one an emitter is newly obligated to satisfy, as
opposed to a retroactive one judging artifacts already on disk) is a different
problem this module does not solve: the matrix only decides whether an existing
required field applies to a given artifact, and documents in
output-format-migrations.md that new-current-skill emission is a prose emitter
obligation, not something the classifier enforces going forward either.
"""

from __future__ import annotations

import re
import subprocess
from functools import cache
from pathlib import Path

LEGACY = "legacy"
CURRENT = "current"
HOTSPOT_V2 = "hotspot_v2"
HOTSPOT_V2_REV = "651ea50"
FINGERPRINT_BOUND = "fingerprint_bound"
FINGERPRINT_BOUND_REV = "44b4c03"
HOTSPOT_TRIAGE = "hotspot_triage"
HOTSPOT_TRIAGE_REV = "7ffd502"
ATTESTATION_SKIP = "attestation_skip"
ATTESTATION_SKIP_REV = "1609cd6"
SKILL_ROOT = Path(__file__).resolve().parent.parent

# Oldest -> newest. Index comparison in `applies()` is what lets a future
# epoch slot in without changing any call site. classify() below checks
# newest-first so a later boundary always wins over an earlier one an
# artifact also satisfies.
EPOCHS: tuple[str, ...] = (
    LEGACY,
    CURRENT,
    HOTSPOT_V2,
    FINGERPRINT_BOUND,
    HOTSPOT_TRIAGE,
    ATTESTATION_SKIP,
)

# Newest -> oldest, paired with each epoch's boundary revision. Extending this
# (and EPOCHS above) is the whole job of adding a future git-ancestry-provable
# epoch; classify() and _is_at_or_after() need no changes.
_PROVABLE_EPOCHS: tuple[tuple[str, str], ...] = (
    (ATTESTATION_SKIP, ATTESTATION_SKIP_REV),
    (HOTSPOT_TRIAGE, HOTSPOT_TRIAGE_REV),
    (FINGERPRINT_BOUND, FINGERPRINT_BOUND_REV),
    (HOTSPOT_V2, HOTSPOT_V2_REV),
)

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
    # [I1] items 1-4 (2026-08-20): challenger/reviewer isolation, transition
    # legality, implementation_review.rounds membership, and G29 schema_version
    # equality all became real enforcement for CURRENT-epoch artifacts only --
    # see _artifact_independence.py, _artifact_transitions.py, and
    # _artifact_review_contract.py for the checkers that read these keys.
    "INDEPENDENCE_ISOLATION_FIELDS": CURRENT,
    "TRANSITIONS_REQUIRED_FIELDS": CURRENT,
    "ROUNDS_REQUIRED_FIELDS": CURRENT,
    "G29_VERSION_EQUALITY": CURRENT,
    # G49: audit_hotspots.py schema v2 became a required Step-0 handoff.
    # Landed 2026-08-24, commit 651ea50.
    "G49_HOTSPOT_SCAN": HOTSPOT_V2,
    # G48 (run_id discipline) is deliberately NOT lifted here. HOTSPOT_V2 satisfies
    # its post-ship epoch condition, but its separate instrumented-pass promotion
    # condition remains; see _artifact_run_identity.py's promotion bar.
    # G32 v4: halt_success_challenge.binding.candidate_fingerprint, required
    # non-empty and equal to the top-level candidate_fingerprint. Landed
    # 2026-08-24, commit 44b4c03 (the prose-only commit that first documents the
    # field; this checker enforcement follows in the same wave, per
    # output-format-migrations.md's two-commit shape for a retroactive field --
    # see _artifact_panel.py's check_g32_halt_success_challenge).
    "G32_FINGERPRINT_BINDING": FINGERPRINT_BOUND,
    # G50: discovery_consumption.hotspot_triage becomes a required, roster-equal
    # Step-0 handoff for HALT_SUCCESS_candidate/HALT_SUCCESS artifacts with
    # non-empty discovery.hotspot_scan.candidates. Landed 2026-08-24, commit
    # 7ffd502 (the prose-only commit that first documents the field; this
    # checker enforcement follows in the same wave, per
    # output-format-migrations.md's two-commit shape for a retroactive field --
    # see _artifact_discovery.py's check_g50_hotspot_triage).
    "G50_HOTSPOT_TRIAGE": HOTSPOT_TRIAGE,
    # G47 skip-reason: loop_result.execution_evidence_skip_reason becomes required
    # (non-empty) whenever execution_evidence is null, a verify-trust pin exists for
    # the resolved repo, and targeted_finding_status != "carried_forward". Landed
    # 2026-08-25, commit 1609cd6 (the prose-only commit that first documents the
    # field; this checker enforcement follows in the same wave, per
    # output-format-migrations.md's two-commit shape for a retroactive field --
    # see _artifact_attestation.py's check_g47_execution_evidence).
    "G47_SKIP_REASON": ATTESTATION_SKIP,
    # Slot for a future client, still unclaimed.
    # "G17_COVERAGE_CITATION": CURRENT,
}


@cache
def _resolve_revision(revision: str) -> str | None:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(SKILL_ROOT),
                "rev-parse",
                "--verify",
                f"{revision}^{{commit}}",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


@cache
def _is_at_or_after(skill_rev: str, boundary_rev: str) -> bool:
    """True when `skill_rev` resolves to `boundary_rev` or a descendant of it.

    Generalized from the original hotspot_v2-only check so a later provable
    epoch (FINGERPRINT_BOUND) reuses the identical ancestry + shallow-clone
    fallback logic instead of a copy-pasted variant.
    """
    resolved = _resolve_revision(skill_rev)
    if resolved is None:
        return False

    boundary = _resolve_revision(boundary_rev)
    if boundary is not None:
        try:
            ancestry = subprocess.run(
                ["git", "-C", str(SKILL_ROOT), "merge-base", "--is-ancestor", boundary, resolved],
                check=False,
                capture_output=True,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        if ancestry.returncode in (0, 1):
            return ancestry.returncode == 0
        return False

    # A depth-1 clone cannot resolve the boundary, but a fresh artifact names
    # the checkout that is executing this validator. Equality proves that case
    # without guessing about any older unresolved revision.
    try:
        shallow = subprocess.run(
            ["git", "-C", str(SKILL_ROOT), "rev-parse", "--is-shallow-repository"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return (
        shallow.returncode == 0
        and shallow.stdout.strip() == "true"
        and resolved == _resolve_revision("HEAD")
    )


def classify(current_review: dict, history: dict | None = None) -> str:
    """Return the ruleset epoch `current_review` was produced under.

    `history` (REVIEW_HISTORY.json, when available) is accepted for interface
    symmetry with the checkers this feeds (G43 already threads history through)
    and for a future signal — e.g. cross-loop skill_rev consistency — but is not
    read today. Classification uses the artifact's `skill_rev` plus only Git facts
    the local skill checkout can prove; unresolved revisions never move forward.

    Checks `_PROVABLE_EPOCHS` newest-first so a skill_rev satisfying more than
    one boundary lands at the newest (a shallow clone's HEAD-equality fallback
    in `_is_at_or_after` cannot tell which boundary it satisfied, so it always
    proves at least the first — newest — one tried).
    """
    skill_rev = current_review.get("skill_rev")
    if not (isinstance(skill_rev, str) and _SKILL_REV_RE.match(skill_rev)):
        return LEGACY
    for provable_epoch, boundary_rev in _PROVABLE_EPOCHS:
        if _is_at_or_after(skill_rev, boundary_rev):
            return provable_epoch
    return CURRENT


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
