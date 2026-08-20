#!/usr/bin/env python3
"""Self-test for `_ruleset_epoch.py` (backlog item [I1]).

Pins three things: the classifier itself (skill_rev -> epoch), the matrix lookup
(`applies`), and the two acceptance directions the [I1] task specifies --
(a) a legacy-epoch artifact missing G43/G46 fields must leave both checks
silent, (b) a current-epoch artifact missing the same fields must still fire
both. Also pins the DOCUMENTED CONSEQUENCE of this module's design choice: a
marker-less artifact is classified legacy, full stop -- there is no signal left
to "prove" it is secretly current, so an artifact that omits `skill_rev` evades
G43/G46 even when every other field says "this is a fresh, current-shaped
loop". That gap is closed on the EMITTER side (skill_rev capture is already
mandatory at schema_version >= 4, startup.md Step -1), not by this validator --
see `_ruleset_epoch.py`'s module docstring for why inferring presence from
absence is exactly the move G19's own docstring rules out.

Run: python3 scripts/_ruleset_epoch_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import copy
import sys

import _canon
import _ruleset_epoch as epoch
from _selftest_lib import load_validator as _load_validator

CANON = _canon.load_canon()

failures: list[str] = []


# --- classify(): skill_rev -> epoch --------------------------------------


def _classify_cases() -> list[tuple[str, dict, str]]:
    """(label, current_review, expected_epoch)."""
    return [
        ("skill_rev absent entirely", {"schema_version": 4}, epoch.LEGACY),
        ("skill_rev explicit null", {"schema_version": 4, "skill_rev": None}, epoch.LEGACY),
        ("skill_rev empty string", {"schema_version": 4, "skill_rev": ""}, epoch.LEGACY),
        ("skill_rev whitespace-only", {"schema_version": 4, "skill_rev": "   "}, epoch.LEGACY),
        ("skill_rev non-string (int)", {"schema_version": 4, "skill_rev": 123}, epoch.LEGACY),
        (
            "skill_rev non-string (dict)",
            {"schema_version": 4, "skill_rev": {"sha": "abc1234"}},
            epoch.LEGACY,
        ),
        (
            "skill_rev uppercase hex (git never emits this)",
            {"schema_version": 4, "skill_rev": "ABC1234"},
            epoch.LEGACY,
        ),
        ("skill_rev too short (3 chars)", {"schema_version": 4, "skill_rev": "abc"}, epoch.LEGACY),
        (
            "skill_rev valid 7-char short SHA",
            {"schema_version": 4, "skill_rev": "2b81c10"},
            epoch.CURRENT,
        ),
        (
            "skill_rev valid full 40-char SHA",
            {"schema_version": 4, "skill_rev": "934682271d8acc5ceaba0cf9e361e7e9a4edefc4"},
            epoch.CURRENT,
        ),
        (
            "skill_rev older real skill_rev (still a valid marker, coarse epoch)",
            {"schema_version": 4, "skill_rev": "f94d802"},
            epoch.CURRENT,
        ),
    ]


for label, artifact, expected in _classify_cases():
    got = epoch.classify(artifact)
    if got != expected:
        failures.append(f"classify: {label}: expected {expected!r}, got {got!r}")

# history is accepted but must never change the verdict (pure function of skill_rev today).
if (
    epoch.classify({"schema_version": 4, "skill_rev": "2b81c10"}, history={"loops": [{}]})
    != epoch.CURRENT
):
    failures.append("classify: passing a history object perturbed the verdict")


# --- applies(): matrix lookup ---------------------------------------------

_LEGACY_ART = {"schema_version": 4}
_CURRENT_ART = {"schema_version": 4, "skill_rev": "2b81c10"}

if not epoch.applies("NOT_IN_THE_MATRIX", _LEGACY_ART):
    failures.append(
        "applies: an unlisted requirement must be unconditionally True (not epoch-gated)"
    )
if not epoch.applies("NOT_IN_THE_MATRIX", _CURRENT_ART):
    failures.append(
        "applies: an unlisted requirement must be unconditionally True (not epoch-gated)"
    )

for req in ("G43_CONVERGENCE_PASS", "G46_REMEDIATION_FIELDS"):
    if epoch.applies(req, _LEGACY_ART):
        failures.append(f"applies: {req} must NOT apply to a legacy-epoch artifact")
    if not epoch.applies(req, _CURRENT_ART):
        failures.append(f"applies: {req} must apply to a current-epoch artifact")

# REQUIREMENT_EPOCHS is DATA: every value must be a real epoch, and both of
# today's two shipped clients (G43, G46) must be entered.
for name in ("G43_CONVERGENCE_PASS", "G46_REMEDIATION_FIELDS"):
    if name not in epoch.REQUIREMENT_EPOCHS:
        failures.append(f"REQUIREMENT_EPOCHS is missing its shipped client {name!r}")
for name, value in epoch.REQUIREMENT_EPOCHS.items():
    if value not in epoch.EPOCHS:
        failures.append(f"REQUIREMENT_EPOCHS[{name!r}] = {value!r} is not a member of EPOCHS")


# --- acceptance: G43/G46 scoped through the classifier, both directions ---


def _g43_shape(skill_rev) -> tuple[dict, dict]:
    """A 9.5-accepted dimension with NO convergence_pass record -- must owe an
    adversarial pass. Two priors satisfy G43's `len(priors) < 2` floor."""
    dim = {"score": 9.5, "delta": "UP", "residual_disposition": "accepted"}
    current = {
        "schema_version": 4,
        "skill_rev": skill_rev,
        "loop": 6,
        "state": "CONTINUE",
        "scorecard": {"domain_modeling": dim},
        "convergence_pass": [],
        "backlog": [],
    }
    history = {
        "loops": [
            {"loop": 4, "scorecard": {"domain_modeling": dim}, "convergence_pass": []},
            {"loop": 5, "scorecard": {"domain_modeling": dim}, "convergence_pass": []},
        ]
    }
    return current, history


def _g46_shape(skill_rev) -> dict:
    """loop_result present but empty -- owes finding_family/effort/repair_revalidation."""
    return {"schema_version": 4, "skill_rev": skill_rev, "loop_result": {}}


va = _load_validator()

legacy_current, legacy_history = _g43_shape(skill_rev=None)
g43_legacy = va.check_g43_convergence_pass(
    copy.deepcopy(legacy_current), copy.deepcopy(legacy_history), CANON
)
if g43_legacy:
    failures.append(
        f"acceptance(a): a legacy-epoch (skill_rev=None) artifact missing its convergence_pass "
        f"record must leave G43 SILENT -- got {[i.message for i in g43_legacy]}"
    )

g46_legacy = va.check_g46_general_remediation_fields(_g46_shape(skill_rev=None), CANON)
if g46_legacy:
    failures.append(
        f"acceptance(a): a legacy-epoch (skill_rev=None) artifact missing loop_result fields "
        f"must leave G46 SILENT -- got {[i.message for i in g46_legacy]}"
    )

current_current, current_history = _g43_shape(skill_rev="2b81c10")
g43_current = va.check_g43_convergence_pass(
    copy.deepcopy(current_current), copy.deepcopy(current_history), CANON
)
if not g43_current:
    failures.append(
        "acceptance(b): a current-epoch artifact missing its convergence_pass record must FIRE G43"
    )

g46_current = va.check_g46_general_remediation_fields(_g46_shape(skill_rev="2b81c10"), CANON)
if len(g46_current) != 3:
    failures.append(
        f"acceptance(b): a current-epoch artifact with loop_result={{}} must fire all 3 G46 "
        f"issues -- got {len(g46_current)}: {[i.message for i in g46_current]}"
    )

# --- documented consequence: a marker-less artifact evades both gates, on ---
# --- purpose. See module docstring above for why the gap is an emitter     ---
# --- obligation (skill_rev capture), not something this validator closes.  ---
evasion_current, evasion_history = _g43_shape(skill_rev=None)
evasion_issues = va.check_g43_convergence_pass(
    copy.deepcopy(evasion_current), copy.deepcopy(evasion_history), CANON
)
if evasion_issues:
    failures.append(
        "documented-consequence: this pins that omitting skill_rev evades G43 -- if it now "
        "fires, either the classifier changed to infer presence from absence (see the module "
        "docstring for why that was rejected) or this case needs re-deriving, not silently "
        "deleting"
    )


if failures:
    for f in failures:
        print(f"FAIL: {f}")
    sys.exit(1)
print(
    f"OK: _ruleset_epoch classifies {len(_classify_cases())} skill_rev shapes, the matrix "
    f"scopes G43/G46 in both directions, and a marker-less artifact's evasion of both is "
    f"pinned as the documented, intentional consequence"
)
sys.exit(0)
