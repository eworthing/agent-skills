"""Shared artifact builders for the G32 v5 panel selftests
(_g32_panel_selftest.py structural cases, _g32_panel_coupling_selftest.py
aggregate/state-coupling and pending-route cases). Not itself a selftest --
deliberately without the _selftest suffix so the selftest sweep
(`for f in scripts/_*_selftest.py`) does not execute it directly.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import candidate_fingerprint as _cfp


def _load_validator():
    path = Path(__file__).with_name("validate-artifact.py")
    spec = importlib.util.spec_from_file_location("_va_g32_panel", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUN_ID = "run-1"
SOURCE_REV = "rev-1"
COMMIT_SHA = "commit-sha-1"
DIGEST = "sha256:" + "a" * 64
STABLE_A = "F-010"
STABLE_B = "F-011"

# candidate_fingerprint() is computed purely from scorecard/findings/discovery, so a
# fixed empty basis gives one constant every HALT_SUCCESS fixture below can share --
# they all use scorecard={}, findings=[] (or an explicit findings=[] override).
FP = _cfp.candidate_fingerprint({"scorecard": {}, "findings": [], "discovery": {}})


def _attempts(diverse=True):
    base = [
        {
            "arm": "residual_refutation",
            "target": "data_flow",
            "what_tried": "reread the residual",
            "why_failed": "still holds",
        }
    ]
    if diverse:
        base.append(
            {
                "arm": "new_finding",
                "target": "simplicity",
                "what_tried": "grep for dead code",
                "why_failed": "none found",
            }
        )
    return base


def _retry_attempt(n, outcome="ok", error=None, duration_ms=1000):
    return {"attempt": n, "outcome": outcome, "error": error, "duration_ms": duration_ms}


def _usage(inp=100, out=50):
    return {"input_tokens": inp, "output_tokens": out, "total_tokens": inp + out}


def _binding(**overrides):
    binding = {
        "run_id": RUN_ID,
        "source_rev": SOURCE_REV,
        "candidate_commit_sha": COMMIT_SHA,
        "candidate_fingerprint": FP,
    }
    binding.update(overrides)
    return binding


def _normalized_evidence(stable_id=STABLE_A, rationale="direct read confirms it"):
    return {"finding_stable_id": stable_id, "spt": {"result": "passed", "rationale": rationale}}


def _raw_finding(title="Duplicated dialog wiring"):
    return {
        "title": title,
        "why_it_matters": "three call sites drift independently",
        "what_is_wrong": "same block copy-pasted three times",
        "evidence": ["src/dialog.py:10", "src/dialog.py:44"],
        "why_weakens_submission": "maintenance burden triples",
        "minimal_correction_path": "extract a shared helper",
    }


def _member(
    index=1,
    outcome="held",
    attempts=None,
    break_evidence=None,
    normalization=None,
    reason="no break found",
    retry_count=1,
    retry_cause=None,
    retry_attempts=None,
    token_usage=None,
    model="challenger-model",
):
    return {
        "member_index": index,
        "challenger_model": model,
        "outcome": outcome,
        "attempts": attempts if attempts is not None else _attempts(),
        "break_evidence": break_evidence,
        "normalization": normalization,
        "reason": reason,
        "retry_count": retry_count,
        "retry_cause": retry_cause,
        "retry_attempts": retry_attempts if retry_attempts is not None else [_retry_attempt(1)],
        "token_usage": token_usage if token_usage is not None else _usage(),
    }


def _challenge(outcome="held", panel=None, **overrides):
    base = {
        "required_panel_size": 3,
        "outcome": outcome,
        "protocol_digest": DIGEST,
        "candidate_binding": _binding(),
        "panel": panel if panel is not None else [_member(1), _member(2), _member(3)],
    }
    base.update(overrides)
    return base


def _success_review(challenge, findings=None):
    return {
        "schema_version": 5,
        "state": "HALT_SUCCESS",
        "halt_subtype": None,
        "run_id": RUN_ID,
        "source_rev": SOURCE_REV,
        "candidate_fingerprint": FP,
        "scorecard": {},
        "findings": findings if findings is not None else [],
        "halt_success_challenge": challenge,
    }


def _nonterminal_review(state, subtype, challenge, findings=None, open_question=None):
    review = {
        "schema_version": 5,
        "state": state,
        "halt_subtype": subtype,
        "findings": findings if findings is not None else [],
        "halt_success_challenge": challenge,
    }
    # user_decision halts carry the question by default so pending-route cases
    # exercise their own defect, not a missing open_question_for_user.
    if subtype == "user_decision" and open_question is None:
        open_question = "which existing finding does this break match?"
    review["open_question_for_user"] = open_question
    return review


def _candidate_review(schema_version=5, challenge=None):
    return {
        "schema_version": schema_version,
        "state": "HALT_SUCCESS_candidate",
        "halt_subtype": None,
        "run_id": RUN_ID,
        "source_rev": SOURCE_REV,
        "candidate_fingerprint": FP,
        "scorecard": {},
        "findings": [],
        "halt_success_challenge": challenge,
    }
