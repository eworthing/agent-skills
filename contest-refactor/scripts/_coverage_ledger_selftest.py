#!/usr/bin/env python3
"""Self-test: the citation-coverage ledger (backlog item 24, slice B).

Design note: analysis/contest-refactor/ITEM24-COVERAGE-UNIT-DESIGN-2026-08-19.md

The property that makes this ledger honest rather than flattering is that it
measures **citation**, not examination, and says so. A loop may read far more
than it cites; the artifact cannot tell the two apart, and closing that gap would
need a model self-report -- the unverifiable kind of evidence item 14 exists to
refuse. So the ledger reports what is actually derivable from committed records
and labels the limit in its own output.

What is pinned here:

  1. `measure` is the literal string "citation" -- if a later edit relabels it
     "examination" the number silently becomes a claim the data cannot support.
  2. DISJOINTNESS: cited + uncited == the denominator, exactly. A file cannot be
     both, and none may go missing -- the derived-terminal-state rule (alibaba's
     "selected equals the disjoint union", adopted in §5 of the design note).
  3. Non-source citations (docs, fixtures) land in `outside_denominator` rather
     than inflating the numerator -- mixing populations would make the ratio
     meaningless in the flattering direction.
  4. STALENESS binds to the recorded revision: a file whose content changed since
     it was cited is `stale`, and staleness is computed from blob shas at the
     recorded sha, never by searching for a revision (the rule item 26a's closure
     established after two prototypes manufactured findings by guessing one).
  5. The registry cross-check: an entry whose `primary_file` no finding ever cited
     is surfaced as an inconsistency between two independently-written records.

Fixtures are a real throwaway git repo built in a tmpdir, because the ledger's
whole contract is about resolving content at a committed revision.

Run: python3 scripts/_coverage_ledger_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import coverage_ledger as cl


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _build_repo(root: Path) -> str:
    """A 4-source-file repo plus one doc and one test file; returns the commit sha."""
    (root / "src").mkdir(parents=True)
    for name, body in (
        ("alpha.py", "def a():\n    return 1\n"),
        ("beta.py", "def b():\n    return 2\n"),
        ("gamma.py", "def c():\n    return 3\n"),
        ("delta.py", "def d():\n    return 4\n"),
        ("test_alpha.py", "def test_a():\n    pass\n"),  # excluded: test file
    ):
        (root / "src" / name).write_text(body, encoding="utf-8")
    (root / "src" / "NOTES.md").write_text("# notes\n", encoding="utf-8")  # excluded: not source
    # A fixture corpus: deliberately-defective source that exists to be graded.
    (root / "src" / "fixtures").mkdir()
    (root / "src" / "fixtures" / "broken.py").write_text("def x(:\n", encoding="utf-8")
    # BenchHype leak class: a hidden build/tooling tree and a Tests/ dir, both
    # nested under the declared source root so they land in the scan and must be
    # excluded by _fs_filters rather than merely never discovered.
    (root / "src" / ".artifacts" / "DerivedData").mkdir(parents=True)
    (root / "src" / ".artifacts" / "DerivedData" / "gen.swift").write_text(
        "struct Gen {}\n", encoding="utf-8"
    )
    (root / "src" / "Tests" / "Support").mkdir(parents=True)
    (root / "src" / "Tests" / "Support" / "Fixture.swift").write_text(
        "struct Fixture {}\n", encoding="utf-8"
    )
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "loop 1: seed")
    return _git(root, "rev-parse", "HEAD")


def main() -> int:
    failures: list[str] = []

    def check(cond: bool, msg: str) -> None:
        if not cond:
            failures.append(msg)

    with tempfile.TemporaryDirectory() as td:
        repo = Path(td) / "repo"
        repo.mkdir()
        sha = _build_repo(repo)

        history = {
            "loops": [
                {
                    "loop": 1,
                    "discovery": {"source_roots": ["src/"]},
                    "findings": [
                        {"stable_id": "F-001", "evidence": ["src/alpha.py:1 -- thing"]},
                        {"stable_id": "F-002", "evidence": ["src/beta.py:2", "src/NOTES.md:1"]},
                    ],
                }
            ]
        }
        registry = {
            "entries": [
                {"stable_id": "F-001", "primary_file": "src/alpha.py"},
                {"stable_id": "F-009", "primary_file": "src/gamma.py"},  # never cited
                # first sighting outside this history (registry outlives history across
                # --reset): must be set aside, not reported as a review inconsistency
                {"stable_id": "F-099", "primary_file": "src/delta.py", "first_seen_loop": 99},
            ]
        }
        led = cl.compute_ledger(repo, history, registry, {1: sha})

        # 1. the measure is labelled honestly
        check(
            led["measure"] == "citation",
            f"measure must be the literal 'citation', got {led['measure']!r} -- relabelling it "
            f"'examination' turns the number into a claim the data cannot support",
        )

        # 2. denominator excludes tests and non-source; disjointness holds exactly
        denom = set(led["denominator"]["files"])
        check(
            denom == {"src/alpha.py", "src/beta.py", "src/gamma.py", "src/delta.py"},
            f"denominator wrong: {sorted(denom)} (test + .md must be excluded)",
        )
        cited, uncited = set(led["sets"]["cited"]), set(led["sets"]["uncited"])
        check(cited & uncited == set(), f"cited and uncited overlap: {sorted(cited & uncited)}")
        check(
            cited | uncited == denom,
            f"cited+uncited != denominator; lost {sorted(denom - (cited | uncited))}, "
            f"gained {sorted((cited | uncited) - denom)}",
        )
        check(cited == {"src/alpha.py", "src/beta.py"}, f"cited wrong: {sorted(cited)}")

        # 2b. exclusions are typed and counted; scanned == included + excluded
        exc = led["denominator"]["excluded_by_reason"]
        check(
            exc.get("fixture_corpus") == 1,
            f"a fixture-corpus file must be excluded with that typed reason, got {exc}",
        )
        check(
            exc.get("test_file") == 1,
            f"the test file must be excluded with reason 'test_file', got {exc}",
        )
        check(
            led["denominator"]["scanned"] == led["denominator"]["count"] + sum(exc.values()),
            "scanned must equal included + excluded -- a denominator that shrinks without "
            "saying how is the survivor-metric hazard",
        )
        check(
            "src/fixtures/broken.py" not in denom,
            "fixture-corpus source must not enter the denominator: it exists to be graded, "
            "not reviewed, and counting it inflates the miss",
        )

        # BenchHype leak class (contest-refactor avalanche plan, Phase 0): a hidden
        # build tree and a Tests/ dir must both be excluded, with a non-empty typed
        # count -- not silently dropped.
        check(
            "src/.artifacts/DerivedData/gen.swift" not in denom,
            "a hidden build/tooling dir (.artifacts) must not enter the denominator",
        )
        check(
            "src/Tests/Support/Fixture.swift" not in denom,
            "a Tests/ dir must not enter the denominator even when the filename "
            "doesn't match any test-suffix pattern",
        )
        check(
            exc.get("vendor_or_build", 0) >= 2,
            f"the hidden dir and the Tests/ dir must both be counted under a typed "
            f"exclusion reason, got {exc}",
        )

        # 3. non-source citations do not inflate the numerator
        check(
            led["sets"]["outside_denominator"] == ["src/NOTES.md"],
            f"non-source citation must land outside the denominator, got "
            f"{led['sets']['outside_denominator']}",
        )

        # 5. registry cross-check surfaces the uncited primary_file
        check(
            led["registry_crosscheck"]["inconsistent"] == ["F-009"],
            f"registry cross-check should flag F-009 (primary_file never cited), got "
            f"{led['registry_crosscheck']['inconsistent']}",
        )
        check(
            led["registry_crosscheck"]["out_of_scope"] == 1,
            f"an entry first seen outside this history must be set aside, not judged: "
            f"{led['registry_crosscheck']}",
        )

        # 4. staleness binds to the recorded revision
        check(
            led["sets"]["stale"] == [], f"nothing should be stale yet, got {led['sets']['stale']}"
        )
        (repo / "src" / "alpha.py").write_text("def a():\n    return 99\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "loop 2: edit alpha")
        led2 = cl.compute_ledger(repo, history, registry, {1: sha})
        check(
            led2["sets"]["stale"] == ["src/alpha.py"],
            f"a cited file edited since its recorded sha must be stale, got "
            f"{led2['sets']['stale']}",
        )
        check(
            "src/beta.py" not in led2["sets"]["stale"],
            "an unchanged cited file must NOT be stale",
        )

        # no revision recorded -> honest unavailable, never a HEAD fallback
        led3 = cl.compute_ledger(repo, history, registry, {})
        check(
            led3["sets"]["stale"] == [] and led3["revision"]["unavailable_loops"] == [1],
            f"with no recorded sha the ledger must report unavailable, not resolve at HEAD: "
            f"{led3['revision']}",
        )

        # --- per-run split: what THIS run cited, not the union of all history --
        # After --reset the loop counter restarts at 1, so REVIEW_HISTORY.json holds
        # two runs whose loop numbers overlap, and run_id is null on the legacy side
        # (14 of 15 loops on the real artifact). A cumulative figure cannot answer
        # "what did this run cover", which is the only question a diagnostic asks.
        two_runs = {
            "loops": [
                history["loops"][0],
                {
                    "loop": 1,  # counter restarted -> new run boundary
                    "run_id": "run-2",
                    "discovery": {"source_roots": ["src/"]},
                    "findings": [
                        {"stable_id": "F-003", "evidence": ["src/beta.py:1", "src/gamma.py:2"]}
                    ],
                },
            ]
        }
        multi = cl.compute_ledger(repo, two_runs, registry, {1: sha})
        runs = multi.get("per_run") or []
        check(len(runs) == 2, f"a restarted loop counter must split runs, got {len(runs)}")
        if len(runs) == 2:
            check(
                runs[1]["run_id"] == "run-2",
                f"run_id must be carried when present, got {runs[1]['run_id']!r}",
            )
            # beta was already cited by run 1; only gamma is new to run 2.
            check(
                runs[1]["first_cited_here"] == 1,
                f"marginal coverage wrong: run 2 cited beta (already seen) + gamma (new), so "
                f"first_cited_here must be 1, got {runs[1].get('first_cited_here')}",
            )
            check(
                runs[1]["cited"] == 2,
                f"run 2 cited 2 in-denominator files, got {runs[1]['cited']}",
            )

        # --- Phase 1: missing-root accounting (avalanche plan) ---------------
        # A declared root that isn't a directory must be counted (not silently
        # dropped -- the same survivor-metric hazard as any other exclusion) AND
        # named, so a typo'd root is diagnosable from the JSON alone.
        history_missing = {
            "loops": [
                {
                    "loop": 1,
                    "discovery": {"source_roots": ["src", "nope"]},
                    "findings": [],
                }
            ]
        }
        led_missing = cl.compute_ledger(repo, history_missing, None, {})
        check(
            led_missing["denominator"]["excluded_by_reason"].get("missing_root") == 1,
            f"a nonexistent declared root must be counted under 'missing_root', got "
            f"{led_missing['denominator']['excluded_by_reason']}",
        )
        check(
            led_missing["denominator"]["missing_roots"] == ["nope"],
            f"the missing root must be named, got {led_missing['denominator'].get('missing_roots')}",
        )

        # --- Phase 1: per_root counts included files under each declared root -
        per_root = led_missing["per_root"]
        check(
            per_root.get("src") == 4,
            f"per_root must count included files under 'src', got {per_root}",
        )
        check(
            per_root.get("nope") == 0,
            f"a missing root contributes zero included files, got {per_root}",
        )

    # --- Phase 1: absolute / '..'-escaping roots -> typed error, exit 2 ------
    # (via the CLI path -- main() is what catches InvalidSourceRoot and turns it
    # into a clean exit 2 instead of an uncaught relative_to() ValueError.)
    with tempfile.TemporaryDirectory() as td:
        abs_repo = Path(td) / "abs_repo"
        abs_repo.mkdir()
        (abs_repo / "REVIEW_HISTORY.json").write_text(
            json.dumps(
                {"loops": [{"loop": 1, "discovery": {"source_roots": ["/etc"]}, "findings": []}]}
            ),
            encoding="utf-8",
        )
        p = subprocess.run(
            [sys.executable, str(SKILL_ROOT / "scripts" / "coverage_ledger.py"), str(abs_repo)],
            capture_output=True,
            text=True,
        )
        check(
            p.returncode == 2,
            f"an absolute source root must exit 2 (plumbing), got {p.returncode}: {p.stderr[:200]}",
        )
        check(
            "source_roots entries must be repo-relative" in p.stderr,
            f"the absolute-root error must name the typed message, got {p.stderr!r}",
        )
        check(
            "Traceback" not in p.stderr,
            f"an invalid root must be a clean error, not a raw traceback: {p.stderr!r}",
        )

        escape_repo = Path(td) / "escape_repo"
        escape_repo.mkdir()
        (escape_repo / "REVIEW_HISTORY.json").write_text(
            json.dumps(
                {"loops": [{"loop": 1, "discovery": {"source_roots": ["../evil"]}, "findings": []}]}
            ),
            encoding="utf-8",
        )
        p = subprocess.run(
            [sys.executable, str(SKILL_ROOT / "scripts" / "coverage_ledger.py"), str(escape_repo)],
            capture_output=True,
            text=True,
        )
        check(
            p.returncode == 2,
            f"a '..'-escaping source root must exit 2 (plumbing), got {p.returncode}",
        )
        check(
            "source_roots entries must be repo-relative" in p.stderr,
            f"the escaping-root error must name the typed message, got {p.stderr!r}",
        )

    # --- Phase 1: source_roots() enumerator + --list-source-roots ------------
    with tempfile.TemporaryDirectory() as td:
        scratch = Path(td) / "scratch"
        for rel in ("PkgKit/Sources/a.swift", "App/b.swift", "tools/c.py"):
            p = scratch / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("// x\n", encoding="utf-8")
        (scratch / "Package.swift").write_text("// pkg\n", encoding="utf-8")
        helper = scratch / "PkgKit" / "Tests" / "Helper.swift"
        helper.parent.mkdir(parents=True, exist_ok=True)
        helper.write_text("// helper\n", encoding="utf-8")

        roots = cl.source_roots(scratch)
        check(
            roots == ["App", "PkgKit/Sources", "tools"],
            f"enumerator must yield exactly the SwiftPM-refined top-level roots, got {roots}",
        )

        p = subprocess.run(
            [
                sys.executable,
                str(SKILL_ROOT / "scripts" / "coverage_ledger.py"),
                str(scratch),
                "--list-source-roots",
            ],
            capture_output=True,
            text=True,
        )
        check(
            p.returncode == 0,
            f"--list-source-roots must exit 0 with no REVIEW_HISTORY.json present, got "
            f"{p.returncode}: {p.stderr[:200]}",
        )
        check(
            p.stdout.splitlines() == roots,
            f"--list-source-roots must print one root per line matching the enumerator, got "
            f"{p.stdout.splitlines()!r}",
        )

        empty = Path(td) / "empty"
        empty.mkdir()
        check(
            cl.source_roots(empty) == ["."],
            f"an empty tree must enumerate to ['.'], got {cl.source_roots(empty)}",
        )

    # --- slice B2: the handoff disclosure, and its honesty guard -------------
    handoff = (SKILL_ROOT / "references" / "halt-handoff.md").read_text(encoding="utf-8")
    if "## Coverage disclosure" not in handoff:
        failures.append(
            "halt-handoff.md lost its Coverage disclosure section -- a converged scorecard goes "
            "back to scoping its claim by dimension only, with nothing about extent"
        )
    if "coverage_ledger.py" not in handoff:
        failures.append("halt-handoff.md no longer tells the loop to run coverage_ledger.py")
    ledger_cmd = handoff.split("coverage_ledger.py")[-1].split("```")[0]
    if "--json" not in ledger_cmd:
        failures.append(
            "the handoff no longer writes the ledger to --json: only the narrated percentage would "
            "survive, and the structured detail (which files, which stale) would be lost"
        )

    # The wording IS the contract. "cited" is a floor on attention; "reviewed"/"examined"
    # would assert something the ledger cannot measure and the artifact cannot support.
    for banned in ('never "reviewed"', "examined"):
        if banned not in handoff:
            failures.append(
                f"halt-handoff.md no longer carries the say-cited-not-{banned} guard -- without "
                f"it the disclosure can be reworded into a claim the data does not support"
            )
            break

    lines = [ln for ln in handoff.splitlines() if ln.startswith("Citation coverage:")]
    if not lines:
        failures.append("the HALT_SUCCESS template no longer renders a 'Citation coverage:' line")
    else:
        rendered = lines[0]
        if "cited" not in rendered:
            failures.append(f"rendered coverage line does not say 'cited': {rendered!r}")
        for overclaim in ("reviewed", "examined", "audited"):
            if overclaim in rendered:
                failures.append(
                    f"rendered coverage line claims {overclaim!r}: {rendered!r} -- the ledger "
                    f"measures citation only"
                )

    # CLI: reports, never gates
    p = subprocess.run(
        [
            sys.executable,
            str(SKILL_ROOT / "scripts" / "coverage_ledger.py"),
            str(SKILL_ROOT.parent),
        ],
        capture_output=True,
        text=True,
    )
    check(p.returncode == 0, f"CLI must exit 0 (report-only), got {p.returncode}: {p.stderr[:200]}")
    p = subprocess.run(
        [
            sys.executable,
            str(SKILL_ROOT / "scripts" / "coverage_ledger.py"),
            str(SKILL_ROOT / "nope"),
        ],
        capture_output=True,
        text=True,
    )
    check(p.returncode == 2, f"missing repo root is plumbing (exit 2), got {p.returncode}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(
        "OK: coverage ledger — citation-labelled, disjoint, revision-bound, registry cross-checked"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
