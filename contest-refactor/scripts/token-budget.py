#!/usr/bin/env python3
"""token-budget.py — tokenizer-based token accounting for the contest-refactor skill.

Every token-saving claim in analysis/contest-refactor/TOKEN-USAGE-AUDIT.md and in the
token-reduction plan depends on this tool, so it is the single source of truth for
"how many tokens does X cost" and "which files does loop step Y load".

Three jobs:
  1. Per-file token counts (`--files`, default: SKILL.md + references/*.md).
  2. The per-loop fixed-reload sum and a full-run projection (`--project --loops N`).
  3. `--loaded-set <step>` — the exact file list a given loop step reloads, per the
     Reference Load Matrix in SKILL.md. This is what the Lever 1 load-path proof checks.

Tokenizer: uses tiktoken (cl100k_base) when importable for real token counts; otherwise
falls back to a deterministic byte/word heuristic. The method in use is printed in every
report so a number is never silently a heuristic. Stdlib-only by default (Python 3.11+),
matching the other contest-refactor validators.

Multiplier basis (TOKEN-USAGE-AUDIT.md): SKILL.md is read once at trigger + once per loop
(×(loops+1)); every other per-loop reference is read once per loop (×loops). A file read
only by the main agent at startup (e.g. references/startup.md) is ×1 and must be passed via
--once so it is not multiplied.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# --- skill layout -----------------------------------------------------------

SKILL_DIR = Path(__file__).resolve().parent.parent
REF = SKILL_DIR / "references"


# --- Reference Load Matrix (source of truth: SKILL.md "## Reference Load Matrix").
# Per-step files the LOOP SUBAGENT reloads from disk every loop. Step labels match
# SKILL.md rows. "step1" includes the read-first SKILL.md (trust-model.md:62 subagent
# template) + the always-included lens set. Stack lens defaults to apple (heaviest);
# pass --lens generic to model the lighter path.
def loaded_set(step: str, lens: str = "apple") -> list[str]:
    stack_lens = "lens-apple.md" if lens == "apple" else "lens-generic.md"
    table: dict[str, list[str]] = {
        # SKILL.md row "Step 1": stack lens + always-included lenses + method + rubric.
        # SKILL.md is read first by the subagent (trust-model.md:62).
        "step1": [
            "SKILL.md",
            stack_lens,
            "lens-security.md",
            "lens-efficiency.md",
            "method.md",
            "method-critic.md",
            "architecture-rubric.md",
            "architecture-rubric-scoring.md",
        ],
        # SKILL.md row "Step 1 emit": output-format trio + validation. halt-handoff.md sits
        # in the matrix's "Always load" cell but is scoped in prose to "when emitting any HALT
        # state" -- most loops are CONTINUE, so it is EXCLUDED here and declared as a known
        # divergence in DECLARED_DIVERGENCES (see --check).
        "step1_emit": [
            "output-format.md",
            "output-format-json.md",
            "output-format-json-rules.md",
            "output-format-markdown.md",
            "validation.md",
        ],
        # SKILL.md row "Step 2": method (Simplify Pressure Test) + rubric (Seam Policy).
        # Both already loaded at step1; listed for routing fidelity, de-duped in the union.
        "step2": ["method.md", "architecture-rubric.md"],
        # SKILL.md row "Step 3": output-format + emit-rules + validation + reviewer + provider.
        "step3": [
            "output-format.md",
            "output-format-json-rules.md",
            "output-format-markdown-archive.md",
            "validation.md",
            "implementation-reviewer.md",
            "provider-adapters.md",
        ],
    }
    if step == "loop":
        seen: dict[str, None] = {}
        for s in ("step1", "step1_emit", "step2", "step3"):
            for f in table[s]:
                seen.setdefault(f, None)
        return list(seen)
    if step not in table:
        raise SystemExit(f"unknown step '{step}'; choose from: {', '.join(sorted(table))}, loop")
    return table[step]


def _resolve(name: str) -> Path:
    return (SKILL_DIR / name) if name == "SKILL.md" else (REF / name)


# --- tokenizer --------------------------------------------------------------


def _make_counter():
    """Return (count_fn, method_label). Prefer tiktoken; else deterministic heuristic."""
    try:
        import tiktoken  # type: ignore[import-not-found]

        enc = tiktoken.get_encoding("cl100k_base")
        return (lambda text: len(enc.encode(text)), "tiktoken/cl100k_base")
    except Exception:
        # Deterministic fallback: max(words/0.75, bytes/4) — both are stable, reproducible
        # functions of the text, so before/after deltas are sound even without a real BPE.
        def heuristic(text: str) -> int:
            words = len(text.split())
            nbytes = len(text.encode("utf-8"))
            return int(max(words / 0.75, nbytes / 4))

        return (heuristic, "heuristic(max(words/0.75, bytes/4))")


# --- reporting --------------------------------------------------------------


def count_files(names: list[str], count_fn) -> dict[str, int]:
    out: dict[str, int] = {}
    for name in names:
        p = _resolve(name)
        if not p.is_file():
            out[name] = -1
            continue
        out[name] = count_fn(p.read_text(encoding="utf-8"))
    return out


def default_file_list() -> list[str]:
    names = ["SKILL.md"]
    names += sorted(p.name for p in REF.glob("*.md"))
    return names


def cmd_files(args, count_fn, method):
    names = args.files or default_file_list()
    counts = count_files(names, count_fn)
    total = sum(c for c in counts.values() if c >= 0)
    if args.json:
        print(json.dumps({"method": method, "files": counts, "total": total}, indent=2))
        return
    print(f"# token counts ({method})")
    for name, c in sorted(counts.items(), key=lambda kv: -kv[1]):
        shown = "MISSING" if c < 0 else f"{c:>7}"
        print(f"{shown}  {name}")
    print(f"{total:>7}  TOTAL ({len([c for c in counts.values() if c >= 0])} files)")


def cmd_loaded_set(args, count_fn, method):
    names = loaded_set(args.loaded_set, lens=args.lens)
    counts = count_files(names, count_fn)
    total = sum(c for c in counts.values() if c >= 0)
    if args.json:
        print(
            json.dumps(
                {
                    "step": args.loaded_set,
                    "lens": args.lens,
                    "method": method,
                    "files": counts,
                    "total": total,
                },
                indent=2,
            )
        )
        return
    print(f"# loaded set: step={args.loaded_set} lens={args.lens} ({method})")
    for name in names:
        c = counts[name]
        shown = "MISSING" if c < 0 else f"{c:>7}"
        print(f"{shown}  {name}")
    print(f"{total:>7}  TOTAL")


def cmd_project(args, count_fn, method):
    """Per-run projection. SKILL.md ×(loops+1); other loop refs ×loops; --once files ×1."""
    loops = args.loops
    loop_files = loaded_set("loop", lens=args.lens)
    counts = count_files(loop_files, count_fn)
    per_loop = sum(c for c in counts.values() if c >= 0)
    skill = counts.get("SKILL.md", 0)
    # SKILL.md gets an extra trigger read; everything else is per-loop only.
    run_total = per_loop * loops + (skill if skill >= 0 else 0)
    once_total = 0
    once_counts = {}
    if args.once:
        once_counts = count_files(args.once, count_fn)
        once_total = sum(c for c in once_counts.values() if c >= 0)
        run_total += once_total
    report = {
        "method": method,
        "lens": args.lens,
        "loops": loops,
        "per_loop_fixed_reload": per_loop,
        "skill_trigger_extra": skill,
        "once_files": once_counts,
        "once_total": once_total,
        "run_total_projection": run_total,
    }
    if args.json:
        print(json.dumps(report, indent=2))
        return
    print(f"# run projection ({method}, lens={args.lens}, loops={loops})")
    print(f"  per-loop fixed reload : {per_loop:>8}")
    print(f"  SKILL.md trigger extra: {skill:>8}")
    if args.once:
        print(f"  once-per-run files    : {once_total:>8}  ({', '.join(args.once)})")
    print(f"  RUN TOTAL projection  : {run_total:>8}")


# --- budget guard (Lever D) ------------------------------------------------
#
# Two independent guards, so neither is derived from the data it polices:
#   1. CEILINGS -- hand-set numbers. Growth past them fails, forcing a deliberate bump.
#   2. DECLARED_DIVERGENCES -- every place the load table above intentionally differs
#      from SKILL.md's Reference Load Matrix, with the reason. Any UNdeclared difference
#      fails, so the table cannot silently drift from the instructions it models.
#
# Motivation: per-loop fixed reload grew 61,100 -> 84,197 tok in six weeks with nothing
# to notice it, and the self-test validated the table against its own copy of the lists.

CEILINGS = {
    # Bumped 82,000 -> 83,300 for backlog item 17 (HALT_EXHAUSTION, Gap 14): SKILL.md,
    # validation.md, output-format-json.md and output-format-json-rules.md each needed a
    # tight addition so the loop knows the state exists and what shape (`exhaustion`
    # object, G45 coupling) to emit for it. Deliberate escape hatch per this dict's own
    # guard comment below -- measured at 83,253 tok, smallest 100-multiple headroom above it.
    # Bumped 83,300 -> 84,200 for backlog item 28 (general remediation fields: finding_family
    # / effort / repair_revalidation, G46): validation.md, output-format-json.md and
    # output-format-json-rules.md each needed an addition describing the new required
    # loop_result fields + the drift_notes coupling. Deliberate escape hatch per this dict's
    # own guard comment below -- measured at 84,115 tok, smallest 100-multiple headroom above it.
    # ONE CEILING PER LENS PATH. A single "loop" ceiling measured on the apple lens left the
    # generic path unpoliced: generic counts ~4.1k fewer tokens, so it sat that far under the
    # apple number and could grow unnoticed until it crossed a ceiling set for a different
    # path. An unmeasured dimension reading as compliant is the same defect shape as
    # tool_runner.py's `absent` != `clean`. --check now polices both paths in one run,
    # regardless of --lens (which still selects the load-matrix comparison only).
    "loop_apple": 84_200,  # per-loop fixed reload, apple lens (measured 84,115)
    "loop_generic": 80_100,  # per-loop fixed reload, generic lens (measured 80,037)
    "skill_md": 10_600,  # SKILL.md trigger read
}

DECLARED_DIVERGENCES = {
    (
        "step1",
        "SKILL.md",
    ): "loop subagent reads SKILL.md first (trust-model.md:62); it is the router, not a reference",
    (
        "step1",
        "lens-apple.md",
    ): 'matrix cell says "Selected stack lens" in prose; expanded to the concrete lens',
    (
        "step1",
        "lens-generic.md",
    ): 'matrix cell says "Selected stack lens" in prose; expanded to the concrete lens',
    ("step1", "lens-security.md"): 'matrix cell says "always-included lenses" in prose; expanded',
    ("step1", "lens-efficiency.md"): 'matrix cell says "always-included lenses" in prose; expanded',
    (
        "step1_emit",
        "output-format-json.md",
    ): "matrix names output-format.md as the index; expanded to the trio it routes to",
    (
        "step1_emit",
        "output-format-markdown.md",
    ): "matrix names output-format.md as the index; expanded to the trio it routes to",
    (
        "step1_emit",
        "halt-handoff.md",
    ): "matrix lists it under Always but scopes it in prose to HALT emits; excluded from the CONTINUE-path baseline",
    (
        "step3",
        "output-format-markdown-archive.md",
    ): "routed by SKILL.md Step-3 sub-step 9 (archive compression), not named in the matrix row",
}

MATRIX_ROWS = {"Step 1": "step1", "Step 1 emit": "step1_emit", "Step 2": "step2", "Step 3": "step3"}


def _matrix_always() -> dict:
    """Parse the 'Always load' column of SKILL.md's Reference Load Matrix."""
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    start = text.index("## Reference Load Matrix")
    section = text[start : text.index("## Loop Isolation", start)]
    out = {}
    for line in section.splitlines():
        if not line.startswith("|") or line.startswith("|---") or "Always load" in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells[0] in MATRIX_ROWS and len(cells) > 1:
            out[MATRIX_ROWS[cells[0]]] = set(re.findall(r"references/([a-z0-9-]+\.md)", cells[1]))
    return out


def cmd_check(args, count_fn, method) -> int:
    failures = []
    matrix = _matrix_always()
    for step, declared in sorted(matrix.items()):
        actual = set(loaded_set(step, args.lens))
        for name in sorted(actual - declared):
            if (step, name) not in DECLARED_DIVERGENCES:
                failures.append(
                    f"[load-matrix] {step}: loads {name!r} but SKILL.md's matrix does not list it "
                    f"(add it to the matrix, or declare it in DECLARED_DIVERGENCES with a reason)"
                )
        for name in sorted(declared - actual):
            if (step, name) not in DECLARED_DIVERGENCES:
                failures.append(
                    f"[load-matrix] {step}: SKILL.md's matrix lists {name!r} but the load table omits it "
                    f"(add it to the table, or declare it in DECLARED_DIVERGENCES with a reason)"
                )

    def _per_loop(lens: str) -> int:
        return sum(
            count_fn(_resolve(f).read_text(encoding="utf-8")) for f in loaded_set("loop", lens)
        )

    # Both paths every run: --lens selects which load-matrix to compare, never which
    # ceiling to enforce. Enforcing only the requested lens is what left generic unpoliced.
    per_loop_by_lens = {"apple": _per_loop("apple"), "generic": _per_loop("generic")}
    skill_md = count_fn((SKILL_DIR / "SKILL.md").read_text(encoding="utf-8"))
    for label, value in (
        ("loop_apple", per_loop_by_lens["apple"]),
        ("loop_generic", per_loop_by_lens["generic"]),
        ("skill_md", skill_md),
    ):
        if value > CEILINGS[label]:
            failures.append(
                f"[ceiling] {label} = {value:,} tok exceeds ceiling {CEILINGS[label]:,}. "
                f"Trim, or raise the ceiling deliberately and say why in the commit."
            )

    # CEILINGS are hand-set from tiktoken counts, so a heuristic run compares numbers from a
    # different measuring stick against them and its verdict means nothing. RUNTIME-COST-AUDIT
    # -2026-08-14 measured this exact case: the same command returned 89,690 / 907,566 against a
    # then-ceiling of 84,197 in a restricted environment -- and exited 0. Refuse to render a
    # verdict instead, with exit 2 (plumbing) so "cannot measure" is distinguishable from
    # exit 1 "over budget"; conflating the two is the same defect Gap 19 flags in
    # exec_replay_grade.py, which folds "inputs missing" into "invariant failed".
    if method != "tiktoken/cl100k_base":
        print(f"# budget guard ({method}, lens={args.lens})")
        print(
            f"budget-guard: CANNOT MEASURE -- ceilings are tiktoken-derived but the tokenizer is "
            f"{method!r}. Install tiktoken (pip install tiktoken); a heuristic count is not "
            f"comparable to these ceilings in either direction."
        )
        return 2

    print(f"# budget guard ({method}, lens={args.lens})")
    print(f"  per-loop (apple)      : {per_loop_by_lens['apple']:>8} / {CEILINGS['loop_apple']:,}")
    print(
        f"  per-loop (generic)    : {per_loop_by_lens['generic']:>8} / {CEILINGS['loop_generic']:,}"
    )
    print(f"  SKILL.md trigger      : {skill_md:>8} / {CEILINGS['skill_md']:,}")
    print(
        f"  load-matrix sync      : {len(matrix)} steps, {len(DECLARED_DIVERGENCES)} declared divergences"
    )
    for f in failures:
        print(f"FAIL {f}")
    print("budget-guard: OK" if not failures else f"budget-guard: {len(failures)} failure(s)")
    return 1 if failures else 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--files", nargs="*", help="file names to count (default: SKILL.md + references/*.md)"
    )
    ap.add_argument(
        "--loaded-set",
        metavar="STEP",
        help="print the file list a loop step reloads: step1|step1_emit|step2|step3|loop",
    )
    ap.add_argument("--project", action="store_true", help="per-run token projection")
    ap.add_argument("--loops", type=int, default=8, help="loop count for --project (default 8)")
    ap.add_argument("--once", nargs="*", help="files read once per run (×1, e.g. startup.md)")
    ap.add_argument(
        "--lens",
        choices=["apple", "generic"],
        default="apple",
        help="stack lens to model (default apple, the heavier path)",
    )
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument(
        "--check",
        action="store_true",
        help="budget guard: fail if the load table drifts from SKILL.md's matrix or a ceiling is exceeded",
    )
    ap.add_argument(
        "--require-tiktoken",
        action="store_true",
        help="exit non-zero unless real tiktoken counts are available (never report heuristic numbers as measured)",
    )
    args = ap.parse_args(argv)

    count_fn, method = _make_counter()
    if args.require_tiktoken and method != "tiktoken/cl100k_base":
        print(
            f"error: --require-tiktoken given but tokenizer is {method!r}; "
            f"install tiktoken (pip install tiktoken)",
            file=sys.stderr,
        )
        return 2
    if args.check:
        return cmd_check(args, count_fn, method)
    if args.loaded_set:
        cmd_loaded_set(args, count_fn, method)
    elif args.project:
        cmd_project(args, count_fn, method)
    else:
        cmd_files(args, count_fn, method)
    return 0


if __name__ == "__main__":
    sys.exit(main())
