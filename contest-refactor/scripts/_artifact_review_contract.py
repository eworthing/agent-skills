"""_artifact_review_contract.py — implementation_review.rounds membership (G-unnumbered)
and G29 schema_version equality (backlog item [I1] items 3 and 4).

Two independently-firing checks, both epoch-scoped (CURRENT only -- see
_ruleset_epoch.py) and both new-module because neither belongs to an existing
`_artifact_*.py` file's own question: `_artifact_review_contract.py` answers
"is this loop's declared contract (review shape, schema version) the one the
current ruleset actually requires", distinct from `_artifact_remediation.py`'s
"is the remediation record shaped honestly" and `_artifact_residual.py`'s
"is the scorecard internally coherent". Same split precedent as
`_artifact_transitions.py`'s own module-boundary note.

## Item 3 — implementation_review.rounds

output-format-json.md:440 fixes the value set: "1 normally; 2 when conditional
-> re-spawn". `type(rounds) is int` (never `isinstance`) because Python's
`bool` is an `int` subclass and `True in (1, 2)` would otherwise silently
pass -- exactly the kind of quiet acceptance a schema-membership check exists
to rule out. Both observed BenchHype production loops emitted `rounds: null`
(the motivating case): LEGACY artifacts tolerate null/missing; a CURRENT
artifact does not, because rounds became load-bearing after this ruleset
started requiring it.

Applies only when `implementation_review` is itself present as a dict --
output-format-json.md documents it as "absent during HALT loops and before
refactor", a legitimate state this check must not misread as a violation.

The conditional-coupling clause ("2 only after a first-pass conditional
verdict") is explicitly NOT enforced here: no durable first-pass verdict
survives into the committed artifact for this check to compare against --
that coupling stays an open residual, not a checked one.

## Item 4 — G29 schema_version equality

validation.md's G29 bullet ("Schema version v3 invariants... no longer
v3-specific") already states the rule this check mechanizes: a newly-emitted
artifact must declare the CAPABILITY-DERIVED current `schema_version`, not a
fixed literal -- v4 on every profile today, v5 only where
canon/panel-certification.toml's `panel_certification` manifest authorizes
the artifact's (provider, loop_model) pair (default-deny; the manifest ships
with zero entries, so every profile is v4 today). This is EQUALITY, not a
blocklist: the register explicitly rejected `!= 3` as an approach, because a
blocklist silently passes every future stale version by omission while
equality only ever passes the one live value.

Derives the required version by calling the SAME manifest lookup the emitter
is required to use (`_panel_capability.emit_check`, per provider-adapters.md's
panel_certification section) rather than hardcoding "4", so this check tracks
the manifest instead of drifting from it independently.

Reading an older artifact (v1-v4, from a prior run) under its own declared
version stays legal per G29's own bullet ("permitted... each entry reads
under its own declared version") -- this check examines only the CURRENT
REVIEW's declared version, at CURRENT epoch, never REVIEW_HISTORY's older
per-loop entries.
"""

from __future__ import annotations

import _panel_capability
import _ruleset_epoch
from _artifact_core import Issue

_ROUNDS_REQUIREMENT = "ROUNDS_REQUIRED_FIELDS"
_VERSION_REQUIREMENT = "G29_VERSION_EQUALITY"


def check_rounds_membership(current_review: dict) -> list[Issue]:
    """implementation_review.rounds must be an int in {1, 2}, at CURRENT epoch,
    whenever implementation_review is present. See module docstring § Item 3.
    """
    issues: list[Issue] = []
    review = current_review.get("implementation_review")
    if not isinstance(review, dict):
        return issues
    if not _ruleset_epoch.applies(_ROUNDS_REQUIREMENT, current_review):
        return issues
    rounds = review.get("rounds")
    if type(rounds) is int and rounds in (1, 2):
        return issues
    issues.append(
        Issue(
            "rounds-membership",
            f"implementation_review.rounds must be an int in {{1, 2}} (1 normally, 2 "
            f"only when a conditional first pass re-spawned the reviewer); got {rounds!r}",
        )
    )
    return issues


def check_g29_schema_version(current_review: dict) -> list[Issue]:
    """schema_version must equal the capability-derived current version, at
    CURRENT epoch. See module docstring § Item 4.
    """
    issues: list[Issue] = []
    if not _ruleset_epoch.applies(_VERSION_REQUIREMENT, current_review):
        return issues
    declared = current_review.get("schema_version")
    if type(declared) is not int:
        issues.append(
            Issue(
                "G29-version-equality",
                f"schema_version must be an int (the capability-derived current "
                f"version); got {declared!r}",
            )
        )
        return issues
    provider = current_review.get("provider") or "unknown"
    model = current_review.get("loop_model") or ""
    result = _panel_capability.emit_check(provider, model)
    required = 5 if result["emit"] == "v5" else 4
    if declared != required:
        issues.append(
            Issue(
                "G29-version-equality",
                f"schema_version declares {declared}, but the capability-derived current "
                f"version for provider={provider!r} loop_model={model!r} is {required} "
                f"(panel_certification lookup: {result['reason']}); a newly-emitted "
                f"artifact's declared version must equal it exactly.",
            )
        )
    return issues
