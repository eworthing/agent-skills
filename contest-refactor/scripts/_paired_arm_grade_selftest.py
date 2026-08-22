#!/usr/bin/env python3
"""Selftest for `paired_arm_grade.py`. Execs the shipped script (item 16): never reimplements it.

Covers the two pieces of preregistered logic it encodes -- the mechanical caught/held rule and the
three ambiguity triggers -- because both decide study outcomes and neither is exercised by any
other selftest. Run directly; exit 0 = pass.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "paired_arm_grade.py"
FAILURES: list[str] = []


def _check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f"  ({detail})" if detail else ""))
    if not ok:
        FAILURES.append(label)


def _run(args: list[str]) -> tuple[int, str, str]:
    p = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def _candidate(tmp: Path, name: str, verdict: dict) -> Path:
    path = tmp / name
    path.write_text("prose\n\n```json\n" + json.dumps(verdict) + "\n```\n")
    return path


def _mech(tmp: Path, scenario: str, verdict: dict, dims: str | None = None) -> str:
    path = _candidate(tmp, "c.md", verdict)
    args = ["mechanical", "--scenario", scenario, "--candidate", str(path)]
    if dims:
        args += ["--dimensions", dims]
    rc, out, err = _run(args)
    assert rc == 0, err
    return json.loads(out)["mechanical_grade"]


def _top_level_triggers() -> None:
    """Pin `check_triggers`' TOP-LEVEL grader checks.

    `check_triggers` fires `grader_uncertain` / `no_cited_span` twice over: once
    on the grade object's own `semantic_grade`, and once per assertion. Only the
    per-assertion pair was covered, so the top-level block could be deleted
    outright with the whole suite still green -- a grader that returns
    `semantic_grade: "uncertain"` overall, or cites a span that is not in the
    candidate text, would have gone unflagged.
    """
    import paired_arm_grade as pag

    text = "the reviewer said the reducer owns the mutation"

    fired = pag.check_triggers(
        "principal-invariant-owner-restraint",
        {"semantic_grade": "uncertain", "assertions": []},
        text,
    )
    _check(
        "top-level semantic_grade 'uncertain' fires grader_uncertain",
        any(f["trigger"] == "grader_uncertain" for f in fired),
        f"fired={fired!r}",
    )

    fired = pag.check_triggers(
        "principal-invariant-owner-restraint",
        {
            "semantic_grade": "pass",
            "semantic_grade_evidence_span": "a span that never appears verbatim",
            "assertions": [],
        },
        text,
    )
    _check(
        "top-level non-verbatim evidence span fires no_cited_span",
        any(f["trigger"] == "no_cited_span" for f in fired),
        f"fired={fired!r}",
    )

    fired = pag.check_triggers(
        "principal-invariant-owner-restraint",
        {
            "semantic_grade": "pass",
            "semantic_grade_evidence_span": "the reducer owns the mutation",
            "assertions": [],
        },
        text,
    )
    _check(
        "top-level verbatim span stays silent (restraint)",
        not any(f["trigger"] in ("grader_uncertain", "no_cited_span") for f in fired),
        f"fired={fired!r}",
    )


def main() -> int:
    _top_level_triggers()
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        flag = "principal-invariant-owner-flag"
        twin = "principal-invariant-owner-restraint"

        print("== mechanical rule: FLAG ==")
        _check(
            "rejected + dimension below 9.5 -> caught",
            _mech(
                tmp,
                flag,
                {
                    "verdict": "rejected",
                    "blocks_95": False,
                    "dimension_scores": {"domain_modeling": 7.0},
                },
            )
            == "caught",
        )
        _check(
            "blocks_95 true + dimension below 9.5 -> caught",
            _mech(
                tmp,
                flag,
                {
                    "verdict": "conditional",
                    "blocks_95": True,
                    "dimension_scores": {"domain_modeling": 8.0},
                },
            )
            == "caught",
        )
        # The AND is load-bearing: a reviewer that blocks while still scoring the dimension at 9.5+
        # has not actually withheld acceptance of that dimension, so it is not a catch.
        _check(
            "blocks_95 true but every dimension >= 9.5 -> missed",
            _mech(
                tmp,
                flag,
                {
                    "verdict": "conditional",
                    "blocks_95": True,
                    "dimension_scores": {"domain_modeling": 9.5},
                },
            )
            == "missed",
        )
        _check(
            "approved -> missed",
            _mech(
                tmp,
                flag,
                {
                    "verdict": "approved",
                    "blocks_95": False,
                    "dimension_scores": {"domain_modeling": 9.6},
                },
            )
            == "missed",
        )
        _check(
            "--dimensions scopes which score counts",
            _mech(
                tmp,
                flag,
                {
                    "verdict": "rejected",
                    "blocks_95": True,
                    "dimension_scores": {"domain_modeling": 9.6, "test_strategy": 6.0},
                },
                dims="domain_modeling",
            )
            == "missed",
            "an off-target dimension held low must not manufacture a catch",
        )

        print("== mechanical rule: TWIN (a strict lower bound, by design) ==")
        _check(
            "approved + not blocking -> held",
            _mech(
                tmp,
                twin,
                {
                    "verdict": "approved",
                    "blocks_95": False,
                    "dimension_scores": {"domain_modeling": 9.5},
                },
            )
            == "held",
        )
        # Score-honesty on an unearned 9.5 reads as over_flagged HERE and that is expected: the
        # plan pins the semantic tier as the operative measure for restraint twins precisely
        # because this tier cannot tell score-honesty from a carve-out flag.
        _check(
            "conditional on the score alone -> over_flagged (under-counts, as documented)",
            _mech(
                tmp,
                twin,
                {
                    "verdict": "conditional",
                    "blocks_95": True,
                    "dimension_scores": {"domain_modeling": 9.0},
                },
            )
            == "over_flagged",
        )

        print("== ambiguity triggers ==")
        cand = _candidate(
            tmp, "cand.md", {"verdict": "approved", "blocks_95": False, "dimension_scores": {}}
        )
        span = "prose"

        def reply(
            assertions: list[dict], grade: str = "held", grade_span: str | None = span
        ) -> Path:
            path = tmp / "reply.md"
            path.write_text(
                "```json\n"
                + json.dumps(
                    {
                        "output_id": "OUT-x",
                        "assertions": assertions,
                        "semantic_grade": grade,
                        "semantic_grade_evidence_span": grade_span,
                        "semantic_grade_rationale": "r",
                    }
                )
                + "\n```\n"
            )
            return path

        idxs = [0, 1, 2, 3]
        clean = [
            {"assertion_index": i, "passed": True, "evidence_span": span, "rationale": "r"}
            for i in idxs
        ]
        rc, out, _ = _run(
            [
                "check-triggers",
                "--scenario",
                twin,
                "--candidate",
                str(cand),
                "--reply",
                str(reply(clean)),
            ]
        )
        _check("all four graded with verbatim spans -> exit 0", rc == 0, f"got {rc}: {out}")

        unsure = [dict(a) for a in clean]
        unsure[2] = {
            "assertion_index": 2,
            "passed": "uncertain",
            "evidence_span": None,
            "rationale": "r",
        }
        rc, out, _ = _run(
            [
                "check-triggers",
                "--scenario",
                twin,
                "--candidate",
                str(cand),
                "--reply",
                str(reply(unsure)),
            ]
        )
        _check("an 'uncertain' assertion fires grader_uncertain -> exit 1", rc == 1, f"got {rc}")
        _check("names the trigger", "grader_uncertain" in out, out[:120])

        # A quote that crosses the candidate's hard line wrap is still a quote. The Phase-2 pilot
        # fired no_cited_span twice on exactly this, and the bias had a direction: longer spans
        # are likelier to cross a newline, so a literal test punished the most thorough citations.
        wrapped_candidate = tmp / "wrapped.md"
        wrapped_candidate.write_text(
            "The coordinator owns the reserve step, and\nthe rollback path is explicit.\n\n"
            "```json\n"
            + json.dumps({"verdict": "approved", "blocks_95": False, "dimension_scores": {}})
            + "\n```\n"
        )
        wrapped_span = "the reserve step, and the rollback path is explicit"
        wrapped = [
            {"assertion_index": i, "passed": True, "evidence_span": wrapped_span, "rationale": "r"}
            for i in idxs
        ]
        rc, out, _ = _run(
            [
                "check-triggers",
                "--scenario",
                twin,
                "--candidate",
                str(wrapped_candidate),
                "--reply",
                str(reply(wrapped, grade_span=wrapped_span)),
            ]
        )
        _check(
            "a quote crossing a hard line wrap is still a citation -> exit 0",
            rc == 0,
            f"got {rc}: {out}",
        )

        # A span the candidate never contained is the "rationale cites no span" trigger: whitespace
        # is normalized, but the token sequence must still be there, so a paraphrase cannot pass.
        fabricated = [dict(a) for a in clean]
        fabricated[0] = {
            "assertion_index": 0,
            "passed": True,
            "evidence_span": "not in the candidate",
            "rationale": "r",
        }
        rc, out, _ = _run(
            [
                "check-triggers",
                "--scenario",
                twin,
                "--candidate",
                str(cand),
                "--reply",
                str(reply(fabricated)),
            ]
        )
        _check("a paraphrased/absent span fires no_cited_span -> exit 1", rc == 1, f"got {rc}")
        _check("names the trigger", "no_cited_span" in out, out[:120])

        stray = [
            *clean,
            {"assertion_index": 99, "passed": True, "evidence_span": span, "rationale": "r"},
        ]
        rc, out, _ = _run(
            [
                "check-triggers",
                "--scenario",
                twin,
                "--candidate",
                str(cand),
                "--reply",
                str(reply(stray)),
            ]
        )
        _check(
            "an assertion outside the residue fires opined_outside_residue -> exit 1",
            rc == 1,
            f"got {rc}",
        )

        rc, out, _ = _run(
            [
                "check-triggers",
                "--scenario",
                twin,
                "--candidate",
                str(cand),
                "--reply",
                str(reply(clean[:2])),
            ]
        )
        _check(
            "silently skipping semantic assertions fires a trigger -> exit 1", rc == 1, f"got {rc}"
        )

        prose_only = tmp / "prose-only.md"
        prose_only.write_text("I could not decide, so here is a paragraph instead.\n")
        rc, _, err = _run(
            [
                "check-triggers",
                "--scenario",
                twin,
                "--candidate",
                str(cand),
                "--reply",
                str(prose_only),
            ]
        )
        _check(
            "a grader reply with no json block -> exit 2 (plumbing)",
            rc == 2,
            f"got {rc}: {err[:80]}",
        )

    if FAILURES:
        print(f"\n_paired_arm_grade_selftest: FAIL ({len(FAILURES)} check(s) failed)")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("\n_paired_arm_grade_selftest: OK (all checks passed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
