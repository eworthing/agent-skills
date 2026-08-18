#!/usr/bin/env python3
"""Semantic-grading helpers for the paired-arm measurement (plan Phase 4; exercised in Phase 2).

Two jobs, both mechanical -- the judgment itself belongs to a dispatched grader subagent, never
to this script or to the host:

  render          interpolate the FROZEN grader prompt (prereg.grading.grader_prompt_file) for one
                  candidate output. The arm label is never interpolated; the caller passes an
                  opaque output id.
  check-triggers  evaluate the three preregistered ambiguity triggers against a grader's JSON
                  reply. All three are decidable by code -- that is why they were preregistered in
                  that form. A trigger routes the slot to a second independent grader; on
                  disagreement a third adjudicator decides and is final. The host never breaks a
                  tie by its own judgment.

Exit codes: 0 ok / 1 a trigger fired (or the reply is unusable as a grade) / 2 plumbing.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import grade_structural  # type: ignore[import-not-found]  # noqa: E402
from _paired_arm_prereg import SKILL_ROOT, load_record  # noqa: E402

STUDY_RECORD = SKILL_ROOT / "evals" / "paired_arm_replication.json"


class Plumbing(Exception):
    pass


def _prereg() -> dict:
    return load_record(STUDY_RECORD)["prereg"]


def _eval_entry(scenario_id: str) -> dict:
    evals = json.loads((SKILL_ROOT / "evals" / "evals.json").read_text())["evals"]
    for e in evals:
        if e.get("name") == scenario_id:
            return e
    raise Plumbing(f"no evals.json entry named {scenario_id!r}")


def semantic_assertions(scenario_id: str) -> list[tuple[int, dict]]:
    """(positional 0-based index in evals.json assertions[], assertion) for the semantic tier."""
    entry = _eval_entry(scenario_id)
    return [(i, a) for i, a in enumerate(entry["assertions"]) if a.get("method") == "semantic"]


def render(scenario_id: str, output_id: str, candidate_path: Path) -> str:
    prereg = _prereg()
    grading = prereg["grading"]
    template = (SKILL_ROOT / grading["grader_prompt_file"]).read_text()
    entry = _eval_entry(scenario_id)
    kind = "restraint" if scenario_id.endswith("-restraint") else "flag"
    lines = []
    for idx, a in semantic_assertions(scenario_id):
        lines.append(f"- `assertion_index: {idx}` — {a['text']}")
    return (
        template.replace("{{OUTPUT_ID}}", output_id)
        .replace("{{SCENARIO_ID}}", scenario_id)
        .replace("{{SCENARIO_KIND}}", kind)
        .replace("{{EXPECTED_OUTPUT}}", entry["expected_output"])
        .replace("{{SEMANTIC_RULE}}", prereg["semantic_rule"])
        .replace("{{ASSERTIONS}}", "\n".join(lines))
        .replace("{{GRADING_SPEC}}", _grading_spec(scenario_id))
        .replace("{{CANDIDATE_OUTPUT}}", candidate_path.read_text())
    )


def _grading_spec(scenario_id: str) -> str:
    """The frozen per-scenario grading spec, or an explicit absence marker.

    Absence is stated, never blank: a grader handed an empty spec section would silently fall back
    to interpreting the answer key itself, which is the exact judgment the spec exists to move
    upstream. An unwritten spec must therefore be visible in the prompt, not invisible."""
    path = SKILL_ROOT / "evals" / "grading-specs" / f"{scenario_id}.md"
    if not path.is_file():
        return (
            "(NO SPEC EXISTS FOR THIS SCENARIO. Grade from the answer key and the tier rule "
            "alone, and treat every borderline call as `uncertain` rather than deciding it.)"
        )
    return path.read_text()


def mechanical_grade(verdict_json: dict, kind: str, target_dimensions: list[str] | None) -> str:
    """The preregistered mechanical rule, verbatim from prereg.mechanical_rule:

        FLAG caught iff (verdict==rejected OR blocks_95==true) AND target dimension_scores < 9.5.
        TWIN held iff verdict==approved AND blocks_95==false (strict floor).

    The twin half is **a strict lower bound and under-counts by design** -- the plan says so, and
    principal_baseline.json bears it out (invariant-owner-restraint: mechanical 0/5 vs semantic
    4/5). A rubric-faithful reviewer may legitimately land `conditional` / `blocks_95: true` on the
    SCORE because the Actor proposed 9.5 with no named residual, while fully clearing the
    carve-out. That is score-honesty, not a restraint miss, so **for restraint twins the semantic
    tier is the operative measure** and this value must never be read as the restraint result on
    its own.
    """
    verdict = verdict_json.get("verdict")
    blocks = verdict_json.get("blocks_95")
    scores = verdict_json.get("dimension_scores") or {}
    if kind == "restraint":
        return "held" if (verdict == "approved" and blocks is False) else "over_flagged"
    relevant = [
        v
        for k, v in scores.items()
        if target_dimensions is None or k in target_dimensions
        if isinstance(v, (int, float))
    ]
    below = any(v < 9.5 for v in relevant)
    return "caught" if (verdict == "rejected" or blocks is True) and below else "missed"


def _extract_json(text: str) -> dict:
    # Same fence-pairing hazard as grade_structural._extract_json: match any language tag so a
    # quoted code block in the grader's own reasoning cannot shift the pairing.
    blocks = re.findall(r"```[A-Za-z0-9_+.-]*[ \t]*\n(.*?)```", text, re.DOTALL)
    if not blocks:
        raise Plumbing("grader reply contains no fenced ```json block")
    return json.loads(blocks[-1])


def check_triggers(scenario_id: str, grade: dict, candidate_text: str) -> list[dict]:
    """The three preregistered ambiguity triggers, evaluated mechanically."""
    fired: list[dict] = []
    residue_indices = {i for i, _ in semantic_assertions(scenario_id)}

    def note(trigger_id: str, detail: str) -> None:
        fired.append({"trigger": trigger_id, "detail": detail})

    if grade.get("semantic_grade") == "uncertain":
        note("grader_uncertain", "semantic_grade is 'uncertain'")
    elif not _spans(grade.get("semantic_grade_evidence_span"), candidate_text):
        note(
            "no_cited_span",
            "semantic_grade is not uncertain but its evidence_span is absent, empty, or "
            "not a verbatim substring of the candidate output",
        )

    for a in grade.get("assertions", []):
        idx = a.get("assertion_index")
        if idx not in residue_indices:
            note(
                "opined_outside_residue",
                f"assertion_index {idx!r} is not in this scenario's semantic residue "
                f"{sorted(residue_indices)}",
            )
            continue
        if a.get("passed") == "uncertain":
            note("grader_uncertain", f"assertion_index {idx}: passed is 'uncertain'")
        elif not _spans(a.get("evidence_span"), candidate_text):
            note(
                "no_cited_span",
                f"assertion_index {idx}: non-uncertain judgment with no verbatim span",
            )
    graded = {a.get("assertion_index") for a in grade.get("assertions", [])}
    missing = residue_indices - graded
    if missing:
        note("opined_outside_residue", f"semantic assertions left ungraded: {sorted(missing)}")
    return fired


def _spans(span: object, candidate_text: str) -> bool:
    """Is `span` a real quote from the candidate -- verbatim in tokens, tolerant of line wrapping?

    A LITERAL substring test looked stricter and was simply wrong. Reviewer prose is hard-wrapped
    at ~95 characters, so any quote crossing a line break fails it while being a perfect quote.
    The Phase-2 pilot fired `no_cited_span` twice on exactly that, and the bias had a direction:
    the longer the cited span the likelier it crosses a newline, so the check punished the most
    thorough citations and would have forced a needless second grader on most slots.

    Collapsing whitespace runs keeps the property that matters -- the exact token sequence must
    appear in the candidate, so a paraphrase still fails -- and drops only the layout accident.
    """
    if not isinstance(span, str) or not span.strip():
        return False
    return " ".join(span.split()) in " ".join(candidate_text.split())


def cmd_render(args: argparse.Namespace) -> int:
    print(render(args.scenario, args.output_id, Path(args.candidate)))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    reply = Path(args.reply).read_text()
    grade = _extract_json(reply)
    candidate = Path(args.candidate).read_text()
    fired = check_triggers(args.scenario, grade, candidate)
    print(json.dumps({"output_id": grade.get("output_id"), "triggers": fired}, indent=2))
    if fired:
        print(
            f"paired_arm_grade: {len(fired)} trigger(s) fired -- this slot is re-graded by a "
            "second independent grader",
            file=sys.stderr,
        )
        return 1
    return 0


def cmd_structural(args: argparse.Namespace) -> int:
    print(json.dumps(grade_structural.grade(Path(args.candidate), args.scenario), indent=2))
    return 0


def cmd_mechanical(args: argparse.Namespace) -> int:
    verdict = grade_structural._load_candidate(Path(args.candidate))
    kind = "restraint" if args.scenario.endswith("-restraint") else "flag"
    dims = args.dimensions.split(",") if args.dimensions else None
    print(
        json.dumps(
            {
                "scenario_id": args.scenario,
                "kind": kind,
                "mechanical_grade": mechanical_grade(verdict, kind, dims),
                "verdict": verdict.get("verdict"),
                "blocks_95": verdict.get("blocks_95"),
                "dimension_scores": verdict.get("dimension_scores"),
            },
            indent=2,
        )
    )
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("--scenario", required=True)
    r.add_argument("--output-id", required=True)
    r.add_argument("--candidate", required=True)
    r.set_defaults(fn=cmd_render)
    c = sub.add_parser("check-triggers")
    c.add_argument("--scenario", required=True)
    c.add_argument("--candidate", required=True)
    c.add_argument("--reply", required=True)
    c.set_defaults(fn=cmd_check)
    s = sub.add_parser("structural")
    s.add_argument("--scenario", required=True)
    s.add_argument("--candidate", required=True)
    s.set_defaults(fn=cmd_structural)
    m = sub.add_parser("mechanical")
    m.add_argument("--scenario", required=True)
    m.add_argument("--candidate", required=True)
    m.add_argument("--dimensions", default=None, help="comma-separated target dimensions")
    m.set_defaults(fn=cmd_mechanical)
    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except Plumbing as exc:
        print(f"paired_arm_grade: PLUMBING: {exc}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"paired_arm_grade: PLUMBING: grader reply is not valid JSON: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
