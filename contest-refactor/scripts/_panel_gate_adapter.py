"""Pre-enforcement behavioral-gate grading adapter (plans/rec1-panel-certification.md
§ Pre-enforcement gate).

Grades staged v5 challenger panels run against evals.json #21 (halt-challenge-flag)
and #22 (halt-challenge-restraint), writes the evidence file
evals/panel_gate_results.json, and owns the ONE shared protocol-digest function
(plan § Version transition -- the same function backs both gate evidence and
runtime capability lookup so the two cannot drift independently).

The digest hashes this file itself (input 10 of compute_protocol_digest) -- so
editing this module invalidates every recorded gate pass, by design.

Never re-derives G32 structural validation: builds a synthetic v5 artifact from
graded panel data and calls _artifact_panel._check_v5_panel_record directly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import _artifact_panel

_DEFAULT_ROOT = Path(__file__).resolve().parent.parent

# Per-member cumulative token cap per transport attempt (plan § Cost).
C_MAX = 150_000

GATE_THRESHOLDS = {
    "panels_per_scenario": 3,
    "panel_size": 3,
    "flag_requirement": "each panel individually contains a structurally valid broke",
    "restraint_requirement": "all nine member verdicts held (3 panels x 3 members)",
}

SPAWN_PROFILE = {
    "provider": "claude_code",
    "mechanism": "in_session_agent_tool",
    "subagent_type": "general-purpose",
    "model_alias": "sonnet",
    "read_only_enforcement": "prompt-level; verdict delivered as final message per halt-verifier.md",
    "tools_expected": ["Read"],
}

BUDGET_ENFORCEMENT = {
    "c_max_tokens": 150000,
    "mode": "post_hoc_discard",
    "detail": (
        "in-session Agent tool cannot preempt mid-session; observed usage is audited "
        "after completion and any member exceeding C_MAX is discarded as "
        "budget_exhausted. Plan § Cost requires stop-before-crossing enforcement for "
        "a capability entry, which this mode does NOT satisfy - hence "
        "capability_recordable: false."
    ),
}

# Verbatim excerpts from plans/rec1-panel-certification.md, frozen at authoring
# time (see module docstring -- input 10 makes any edit here, or to the plan
# text these mirror, a fresh digest anyway).
PROTOCOL_ROUTING_STAGING = """1. Launch **member 1**. A **structurally valid break** demotes immediately; members 2 and 3 are never launched.
2. Member 1 exhausting its retry envelope routes `verification_blocked`; members 2 and 3 are never launched.
3. Only on member 1 `held` do **members 2 and 3 launch in parallel**.

| # | condition | aggregate | outcome |
|---|---|---|---|
| 0 | any member's break hits an **ambiguous registry match** | `pending` | `HALT_STAGNATION` subtype `user_decision`, `open_question_for_user` non-null |
| 1 | any member returned a **structurally valid** `broke`, **and** the fix needs a CLAUDE-md Stop/Ask decision | `broke` | `HALT_STAGNATION` subtype `user_decision`, `open_question_for_user` non-null |
| 2 | any member returned a **structurally valid** `broke` | `broke` | demote — CONTINUE with the finding as Priority 1 (as today) |
| 3 | fewer than 3 members returned a usable verdict after the retry envelope | `blocked` | `HALT_STAGNATION` subtype `verification_blocked` |
| 4 | all 3 returned `held` | `held` | promote to terminal `HALT_SUCCESS` |

A `broke` is **structurally valid** only if, after normalization, it carries a resolved `finding_stable_id` and an `spt` record whose `result` is `"passed"` with a non-empty rationale (both defined below). A break that is still malformed after the member's retry envelope is **normalized to `outcome: "unavailable"`** with `retry_cause: "malformed_json"` — it never persists as a schema-invalid `broke`, and it therefore counts toward row 3, not rows 1–2. Otherwise a garbled response becomes a free demotion.
"""

PROTOCOL_NORMALIZATION = """1. **Resolve every break against the evolving staged registry**, per Method Step 1.5, in `member_index` order. Match → reuse `stable_id`. Miss → reserve `F-{next_serial}` and increment, so `stable_id == next_serial - 1` as rule #21 requires. The registry is *staged*, so a second break that matches the first's newly reserved entry resolves to it rather than allocating a duplicate.
2. **Deduplicate by `stable_id`.** Two members can report the same defect; that is one finding, not two.
3. **Order the distinct findings** by Priority, lowest `member_index` first.
4. **Assign `loop_local_id`** across that ordered set.
5. **Append one occurrence per distinct `stable_id`** — `{loop: N, loop_local_id, status: "open"}`. This must follow step 4: the occurrence stub *contains* `loop_local_id`, so appending it during resolution would write an ID that does not exist yet.
6. **Write `findings[]`**, one entry per distinct resolved break.
7. **Write backlog items**, each carrying `stable_id` per G42; the Priority-1 item is the first in the ordered set.
8. **Rewrite `break_evidence`** to normalized form on each member record; members that deduplicated to a shared `stable_id` all reference it.
9. **Mirror into `REVIEW_HISTORY.json.loops[-1]`** (G18 parsed-dict equality).
"""

PROTOCOL_V5_SCHEMA = """{
  "required_panel_size": 3,               // int, fixed at 3 in v5
  "outcome": "held",                      // aggregate: held | broke | blocked | pending
  "protocol_digest": "sha256:…",          // stamped at panel creation; what resume/rollback compares
  "candidate_binding": {                  // immutable; present on EVERY path
    "run_id": "…",
    "source_rev": "…",
    "candidate_commit_sha": "…",
    "candidate_fingerprint": "…"          // v4+ field, reused
  },
  "panel": [                              // ordered; member 1 is the staged first launch
    {
      "member_index": 1,                  // 1-based, matches launch order
      "challenger_model": "…",
      "outcome": "held",                  // held | broke | unavailable
      "attempts": [ /* {arm, target, what_tried, why_failed} — as today */ ],
      "break_evidence": null,             // required non-null iff outcome == "broke"
                                          // NORMALIZED form: { finding_stable_id, spt: {result, rationale} }
                                          // (the raw challenger returns a different shape — see below)
      "normalization": null,              // null | "pending_user_decision" | "deferred_by_pending_registry_decision"
                                          // non-null ONLY under aggregate outcome "pending" (raw break_evidence)
      "reason": "…",
      "retry_count": 1,                   // int ∈ {1, 2} — mirrors rule #25 exactly
      "retry_cause": null,                // null | "timeout" | "spawn_error" | "malformed_json"
                                          //      | "budget_exhausted"  (v5 addition)
                                          // non-null iff retry_count == 2
      "retry_attempts": [                 // length == retry_count
        { "attempt": 1, "outcome": "ok", "error": null, "duration_ms": 7250 }
      ],
      "token_usage": {                    // aggregate across ALL transport attempts
        "input_tokens": 0, "output_tokens": 0, "total_tokens": 0
      }
    }
    // members 2 and 3 present only if member 1 held
  ]
}"""


def _canon_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def _framed(label: str, data: bytes) -> bytes:
    return label.encode() + b"\x00" + str(len(data)).encode() + b"\x00" + data


def _build_inputs(root: Path) -> list[tuple[str, bytes]]:
    evals = json.loads((root / "evals" / "evals.json").read_text())["evals"]
    by_id = {e.get("id"): e for e in evals}
    scenario_flag = (
        root / "evals" / "scenarios" / "halt-challenge-flag" / "scenario.md"
    ).read_bytes()
    scenario_restraint = (
        root / "evals" / "scenarios" / "halt-challenge-restraint" / "scenario.md"
    ).read_bytes()
    gate_scenarios = (
        _canon_json([by_id[21], by_id[22]]) + b"\x00" + scenario_flag + b"\x00" + scenario_restraint
    )
    return [
        ("input-01", (root / "references" / "halt-verifier.md").read_bytes()),
        ("input-02", PROTOCOL_ROUTING_STAGING.encode()),
        ("input-03", PROTOCOL_NORMALIZATION.encode()),
        ("input-04", PROTOCOL_V5_SCHEMA.encode()),
        ("input-05", _canon_json(GATE_THRESHOLDS)),
        ("input-06", _canon_json({"claude_code/sonnet-in-session": C_MAX})),
        ("input-07", _canon_json(SPAWN_PROFILE)),
        ("input-08", _canon_json(BUDGET_ENFORCEMENT)),
        ("input-09", gate_scenarios),
        ("input-10", (root / "scripts" / "_panel_gate_adapter.py").read_bytes()),
    ]


def compute_protocol_digest(root: Path | None = None) -> str:
    h = hashlib.sha256()
    for label, data in _build_inputs(root or _DEFAULT_ROOT):
        h.update(_framed(label, data))
    return "sha256:" + h.hexdigest()


def digest_manifest(root: Path | None = None) -> list[tuple[str, int]]:
    return [(label, len(data)) for label, data in _build_inputs(root or _DEFAULT_ROOT)]


def _first_balanced_object(text: str) -> str | None:
    """First balanced {...} span, brace-scanning past braces inside strings."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)```", re.DOTALL)


def extract_member_json(text: str) -> dict | None:
    """Tolerant extraction of the challenger's final-message JSON: whole string,
    then a fenced ```json / ``` block, then the first balanced {...} span. A
    candidate that decodes to a str (a member seen double-encoding its verdict
    -- the whole object serialized again as a JSON string) is decoded once
    more before the dict check."""
    if not isinstance(text, str):
        return None
    candidates = [text]
    fence = _FENCE_RE.search(text)
    if fence:
        candidates.append(fence.group(1))
    brace_span = _first_balanced_object(text)
    if brace_span is not None:
        candidates.append(brace_span)
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(parsed, str):
            try:
                parsed = json.loads(parsed)
            except (json.JSONDecodeError, TypeError):
                continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _is_valid_raw_break(evidence) -> bool:
    return (
        isinstance(evidence, dict)
        and isinstance(evidence.get("finding"), dict)
        and isinstance(evidence.get("spt"), dict)
    )


def _assemble_member(capture_member: dict) -> dict:
    """Transport fields (member_index, retry envelope, token_usage) come from the
    capture; content fields (outcome, attempts, reason, break_evidence) come from
    parsing raw_response_text. Unparseable, or a 'broke' whose break_evidence
    isn't a dict carrying dict finding+spt, converts to outcome 'unavailable'
    (plan: a break still malformed after the envelope never persists as a
    schema-invalid broke)."""
    retry_attempts = capture_member.get("retry_attempts") or []
    transport = {
        "member_index": capture_member["member_index"],
        "normalization": None,
        "retry_count": len(retry_attempts),
        "retry_cause": capture_member.get("retry_cause"),
        "retry_attempts": retry_attempts,
        "token_usage": capture_member.get("token_usage"),
    }
    parsed = extract_member_json(capture_member.get("raw_response_text", ""))
    if not isinstance(parsed, dict):
        return {
            **transport,
            "challenger_model": None,
            "outcome": "unavailable",
            "attempts": None,
            "reason": "malformed challenger response after retry envelope",
            "break_evidence": None,
        }
    outcome = parsed.get("outcome")
    break_evidence = parsed.get("break_evidence")
    if outcome == "broke" and not _is_valid_raw_break(break_evidence):
        return {
            **transport,
            "challenger_model": parsed.get("challenger_model"),
            "outcome": "unavailable",
            "attempts": parsed.get("attempts"),
            "reason": "malformed break: break_evidence missing a finding or spt object",
            "break_evidence": None,
        }
    return {
        **transport,
        "challenger_model": parsed.get("challenger_model"),
        "outcome": outcome,
        "attempts": parsed.get("attempts"),
        "reason": parsed.get("reason"),
        "break_evidence": break_evidence if outcome == "broke" else None,
    }


def normalize_panel(
    member_records: list[dict],
) -> tuple[list[dict], list[dict], str, str, str | None]:
    """Gate-scope version of the plan's break-normalization transaction (plan §
    Break normalization). The gate registry starts empty for every panel and no
    cross-member dedup is attempted against it -- dedup against a real registry
    is main's Method Step 1.5, out of gate scope.

    Precedence rows 0/1 (ambiguous registry match, Stop/Ask) cannot occur at gate
    scope: an empty registry has no prior entry to collide with, so no break is
    ever ambiguous, and neither eval scenario poses a CLAUDE-md Stop/Ask decision.
    """
    records = [dict(m) for m in member_records]
    findings: list[dict] = []
    serial = 1
    for m in records:
        if m.get("outcome") != "broke":
            continue
        raw = m.get("break_evidence")
        finding = dict(raw["finding"])
        spt = raw["spt"]
        stable_id = f"F-{serial}"
        loop_local_id = f"F{serial}"
        serial += 1
        finding["stable_id"] = stable_id
        finding["loop_local_id"] = loop_local_id
        findings.append(finding)
        m["break_evidence"] = {"finding_stable_id": stable_id, "spt": spt}

    outcomes = [m.get("outcome") for m in records]
    if "broke" in outcomes:
        aggregate = "broke"
    elif len(records) == 3 and all(o == "held" for o in outcomes):
        aggregate = "held"
    else:
        aggregate = "blocked"
    state, subtype = {
        "broke": ("CONTINUE", None),
        "held": ("HALT_SUCCESS", None),
        "blocked": ("HALT_STAGNATION", "verification_blocked"),
    }[aggregate]
    return records, findings, aggregate, state, subtype


def _budget_audit(records: list[dict]) -> tuple[dict, str | None, bool]:
    per_member = []
    max_total = None
    violation = False
    for m in records:
        usage = m.get("token_usage")
        total = usage.get("total_tokens") if isinstance(usage, dict) else None
        per_member.append({"member_index": m.get("member_index"), "total_tokens": total})
        if total is not None:
            if max_total is None or total > max_total:
                max_total = total
            if total > C_MAX:
                violation = True
    exhaustion_cause = "budget_exhausted" if violation else None
    return (
        {"per_member": per_member, "max_member_total_tokens": max_total},
        exhaustion_cause,
        violation,
    )


def _structural_grade(
    scenario: str,
    panel_index: int,
    skill_rev: str,
    digest: str,
    aggregate: str,
    state: str,
    subtype: str | None,
    records: list[dict],
    findings: list[dict],
) -> tuple[bool, list[str]]:
    binding = {
        "run_id": f"panel-gate-{scenario}-p{panel_index}",
        "source_rev": skill_rev,
        "candidate_commit_sha": skill_rev,
        "candidate_fingerprint": f"gate-{scenario}",
    }
    challenge = {
        "required_panel_size": 3,
        "outcome": aggregate,
        "protocol_digest": digest,
        "candidate_binding": binding,
        "panel": records,
    }
    review = {
        "schema_version": 5,
        "state": state,
        "halt_subtype": subtype,
        "findings": findings,
        "open_question_for_user": None,
    }
    top = {}
    if state == "HALT_SUCCESS":
        top = {
            "top_run_id": binding["run_id"],
            "top_source_rev": binding["source_rev"],
            "top_fingerprint": binding["candidate_fingerprint"],
        }
    issues = _artifact_panel._check_v5_panel_record(review, challenge, state, subtype, **top)
    return not issues, [f"{i.rule}: {i.message}" for i in issues]


_FLAG_TEXT_FIELDS = ("title", "what_is_wrong", "why_weakens_submission", "why_it_matters")
_FLAG_OWNERSHIP_TERMS = ("tabview", "deeplinkrouter", "loginviewmodel")
_RESTRAINT_BAD_TERMS = ("979", "file length", "file-length", " loc")


def _finding_text(finding: dict) -> str:
    parts = [str(finding.get(f, "")) for f in _FLAG_TEXT_FIELDS]
    evidence = finding.get("evidence")
    if isinstance(evidence, list):
        parts.extend(str(e) for e in evidence)
    return " ".join(parts).lower()


def _breaking_members(records: list[dict], findings: list[dict]) -> list[tuple[dict, dict]]:
    """(member, finding) pairs for members whose break normalized cleanly --
    outcome 'broke' with a resolved finding_stable_id. A malformed break was
    already converted to 'unavailable' during MEMBER-RECORD ASSEMBLY."""
    by_id = {f["stable_id"]: f for f in findings}
    pairs = []
    for m in records:
        if m.get("outcome") != "broke":
            continue
        evidence = m.get("break_evidence")
        stable_id = evidence.get("finding_stable_id") if isinstance(evidence, dict) else None
        if stable_id in by_id:
            pairs.append((m, by_id[stable_id]))
    return pairs


def _grade_flag_semantics(records: list[dict], findings: list[dict]) -> tuple[bool, list[dict]]:
    breaking = _breaking_members(records, findings)
    f1_pass = bool(breaking)

    best = None
    best_score = -1
    for _member, finding in breaking:
        text = _finding_text(finding)
        f2 = "selectedtab" in text and sum(t in text for t in _FLAG_OWNERSHIP_TERMS) >= 2
        f4 = finding.get("severity") in ("Serious deduction", "Likely disqualifier")
        score = int(f2) + int(f4)
        if score > best_score:
            best_score, best = score, (f2, f4)
    f2_pass, f4_pass = best if best else (False, False)
    f3_pass = f2_pass  # deterministic proxy, see detail below

    checks = [
        {
            "assertion": "f1-broke-maps-rejected",
            "passed": f1_pass,
            "detail": f"{len(breaking)} structurally-usable broke member(s)",
        },
        {
            "assertion": "f2-names-split-ownership",
            "passed": f2_pass,
            "detail": (
                "best breaking finding names selectedTab plus >=2 of "
                "TabView/DeepLinkRouter/LoginViewModel"
                if f2_pass
                else "no breaking finding names selectedTab plus >=2 of the concrete writer sites"
            ),
        },
        {
            "assertion": "f3-rejects-compliance-rationale",
            "passed": f3_pass,
            "detail": (
                "deterministic proxy: passes iff f2 passes -- the deterministic grader treats "
                "naming the concrete writer sites as refusing the HR-1 compliance rationale; "
                "raw_member_responses are retained for human re-grade"
            ),
        },
        {
            "assertion": "f4-severity-serious-or-worse",
            "passed": f4_pass,
            "detail": (
                "best breaking finding's severity is Serious deduction or Likely disqualifier"
                if f4_pass
                else "no breaking finding reached Serious-or-worse severity"
            ),
        },
    ]
    return f1_pass and f2_pass and f4_pass, checks


def _grade_restraint_semantics(
    records: list[dict], findings: list[dict]
) -> tuple[bool, list[dict]]:
    held_count = sum(1 for m in records if m.get("outcome") == "held")
    r1_pass = len(records) == 3 and held_count == 3

    flagged = False
    for _member, finding in _breaking_members(records, findings):
        if any(term in _finding_text(finding) for term in _RESTRAINT_BAD_TERMS):
            flagged = True
            break
    r2_pass = not flagged

    checks = [
        {
            "assertion": "r1-all-held",
            "passed": r1_pass,
            "detail": f"{held_count}/{len(records)} members held",
        },
        {
            "assertion": "r2-no-file-length-break",
            "passed": r2_pass,
            "detail": (
                "vacuously true: r1 holds, no broke member exists"
                if r1_pass
                else (
                    "a broke member's finding cites the file-length residual alone"
                    if flagged
                    else "no break cites file length"
                )
            ),
        },
    ]
    return r1_pass and r2_pass, checks


def _grade_panel(provider, model, scenario: str, skill_rev: str, digest: str, panel: dict) -> dict:
    panel_index = panel["panel_index"]
    capture_members = panel["members"]
    raw_member_responses = [m["raw_response_text"] for m in capture_members]
    member_records = [_assemble_member(m) for m in capture_members]
    records, findings, aggregate, state, subtype = normalize_panel(member_records)
    observed_usage, exhaustion_cause, budget_violation = _budget_audit(records)
    structural_pass, structural_issues = _structural_grade(
        scenario, panel_index, skill_rev, digest, aggregate, state, subtype, records, findings
    )
    if scenario == "halt-challenge-flag":
        semantic_pass, semantic_checks = _grade_flag_semantics(records, findings)
    elif scenario == "halt-challenge-restraint":
        semantic_pass, semantic_checks = _grade_restraint_semantics(records, findings)
    else:
        semantic_pass, semantic_checks = (
            False,
            [
                {
                    "assertion": "unknown-scenario",
                    "passed": False,
                    "detail": f"no semantic grader for scenario={scenario!r}",
                }
            ],
        )
    return {
        "provider": provider,
        "model": model,
        "skill_rev": skill_rev,
        "protocol_digest": digest,
        "scenario": scenario,
        "panel_index": panel_index,
        "raw_member_responses": raw_member_responses,
        "normalized_member_records": records,
        "aggregate_outcome": aggregate,
        "state": state,
        "halt_subtype": subtype,
        "findings": findings,
        "enforced_C_max": C_MAX,
        "observed_usage": observed_usage,
        "exhaustion_cause": exhaustion_cause,
        "budget_violation": budget_violation,
        "structural_pass": structural_pass,
        "structural_issues": structural_issues,
        "semantic_pass": semantic_pass,
        "semantic_checks": semantic_checks,
    }


def _panel_ok(run: dict) -> bool:
    return run["structural_pass"] and run["semantic_pass"] and not run["budget_violation"]


def _scenario_gate(runs: list[dict]) -> dict:
    def _eval(name: str, require_all_held: bool) -> dict:
        panels = [r for r in runs if r["scenario"] == name]
        need = GATE_THRESHOLDS["panels_per_scenario"]
        n_pass = sum(1 for r in panels if _panel_ok(r))
        passed = len(panels) == need and n_pass == need
        detail = f"{n_pass}/{len(panels)} panels passing (need {need})"
        if require_all_held:
            n_held = sum(1 for r in panels if r["aggregate_outcome"] == "held")
            detail += f"; {n_held}/{len(panels)} held"
            passed = passed and n_held == len(panels)
        return {"pass": passed, "detail": detail}

    return {
        "halt-challenge-flag": _eval("halt-challenge-flag", require_all_held=False),
        "halt-challenge-restraint": _eval("halt-challenge-restraint", require_all_held=True),
    }


def _measured_C(runs: list[dict]) -> dict:
    per_member = []
    max_total = None
    for r in runs:
        for m in r["observed_usage"]["per_member"]:
            per_member.append(
                {
                    "scenario": r["scenario"],
                    "panel_index": r["panel_index"],
                    "member_index": m["member_index"],
                    "total_tokens": m["total_tokens"],
                }
            )
            if m["total_tokens"] is not None and (
                max_total is None or m["total_tokens"] > max_total
            ):
                max_total = m["total_tokens"]
    return {
        "per_member": per_member,
        "max_member_total_tokens": max_total,
        "note": "first measured C per plan § Cost; token_usage aggregated across all transport attempts per member",
    }


def grade_captures(captures: list[dict], skill_rev: str) -> dict:
    digest = compute_protocol_digest()
    runs: list[dict] = []
    for capture in captures:
        provider = capture.get("provider")
        model = capture.get("model")
        scenario = capture.get("scenario")
        for panel in capture.get("panels", []):
            runs.append(_grade_panel(provider, model, scenario, skill_rev, digest, panel))

    scenario_gate = _scenario_gate(runs)
    gate_pass = (
        scenario_gate["halt-challenge-flag"]["pass"]
        and scenario_gate["halt-challenge-restraint"]["pass"]
    )

    return {
        "generated_by": "scripts/_panel_gate_adapter.py",
        "protocol_digest": digest,
        "skill_rev": skill_rev,
        "enforced_C_max": C_MAX,
        "budget_enforcement": BUDGET_ENFORCEMENT,
        "spawn_profile": SPAWN_PROFILE,
        "gate_thresholds": GATE_THRESHOLDS,
        "runs": runs,
        "scenario_gate": scenario_gate,
        "profile_verdict": {
            "provider": captures[0].get("provider") if captures else None,
            "model": captures[0].get("model") if captures else None,
            "gate_pass": gate_pass,
            "capability_recordable": False,
            "reasons": [
                "budget enforcement is post_hoc_discard; plan § Cost requires stop-before-crossing "
                "enforcement for any capability entry",
                "protocol_digest will change when step-3 prose lands in halt-verifier.md; the gate "
                "re-runs against the frozen protocol before any capability entry is recorded",
            ],
        },
        "measured_C": _measured_C(runs),
    }


def _cmd_digest(args: argparse.Namespace) -> int:
    print(compute_protocol_digest())
    if args.manifest:
        for label, length in digest_manifest():
            print(f"{label}\t{length}")
    return 0


def _cmd_grade(args: argparse.Namespace) -> int:
    captures = [json.loads(Path(p).read_text()) for p in args.capture]
    results = grade_captures(captures, args.skill_rev)
    out_path = Path(args.out) if args.out else _DEFAULT_ROOT / "evals" / "panel_gate_results.json"
    out_path.write_text(json.dumps(results, indent=2) + "\n")
    for name, info in results["scenario_gate"].items():
        print(f"{name}: {'PASS' if info['pass'] else 'FAIL'} - {info['detail']}")
    gate_pass = results["profile_verdict"]["gate_pass"]
    print(f"gate_pass={gate_pass} digest={results['protocol_digest']}")
    return 0 if gate_pass else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Panel gate grading adapter")
    sub = parser.add_subparsers(dest="command", required=True)

    p_digest = sub.add_parser("digest", help="print the protocol digest")
    p_digest.add_argument(
        "--manifest", action="store_true", help="also print per-input byte lengths"
    )
    p_digest.set_defaults(func=_cmd_digest)

    p_grade = sub.add_parser("grade", help="grade captured panel runs")
    p_grade.add_argument(
        "--capture", action="append", required=True, help="capture JSON file (repeatable)"
    )
    p_grade.add_argument("--skill-rev", required=True)
    p_grade.add_argument("--out", help="output path (default evals/panel_gate_results.json)")
    p_grade.set_defaults(func=_cmd_grade)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
