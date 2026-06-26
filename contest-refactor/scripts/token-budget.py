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
        "step1": ["SKILL.md", stack_lens, "lens-security.md",
                  "method.md", "architecture-rubric.md",
                  "architecture-rubric-scoring.md"],
        # SKILL.md row "Step 1 emit": output-format trio + validation (+ halt-handoff
        # conditional, counted because most loops route through a HALT check at emit).
        "step1_emit": ["output-format.md", "output-format-json.md",
                       "output-format-json-rules.md",
                       "output-format-markdown.md", "validation.md"],
        # SKILL.md row "Step 2": method (Simplify Pressure Test) + rubric (Seam Policy).
        # Both already loaded at step1; listed for routing fidelity, de-duped in the union.
        "step2": ["method.md", "architecture-rubric.md"],
        # SKILL.md row "Step 3": output-format + emit-rules + validation + reviewer + provider.
        "step3": ["output-format.md", "output-format-json-rules.md", "validation.md",
                  "implementation-reviewer.md", "provider-adapters.md"],
    }
    if step == "loop":
        seen: dict[str, None] = {}
        for s in ("step1", "step1_emit", "step2", "step3"):
            for f in table[s]:
                seen.setdefault(f, None)
        return list(seen)
    if step not in table:
        raise SystemExit(f"unknown step '{step}'; choose from: "
                         f"{', '.join(sorted(table))}, loop")
    return table[step]


def _resolve(name: str) -> Path:
    return (SKILL_DIR / name) if name == "SKILL.md" else (REF / name)


# --- tokenizer --------------------------------------------------------------

def _make_counter():
    """Return (count_fn, method_label). Prefer tiktoken; else deterministic heuristic."""
    try:
        import tiktoken  # type: ignore
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
        print(json.dumps({"step": args.loaded_set, "lens": args.lens,
                          "method": method, "files": counts, "total": total}, indent=2))
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
        "method": method, "lens": args.lens, "loops": loops,
        "per_loop_fixed_reload": per_loop,
        "skill_trigger_extra": skill,
        "once_files": once_counts, "once_total": once_total,
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


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--files", nargs="*", help="file names to count (default: SKILL.md + references/*.md)")
    ap.add_argument("--loaded-set", metavar="STEP",
                    help="print the file list a loop step reloads: step1|step1_emit|step2|step3|loop")
    ap.add_argument("--project", action="store_true", help="per-run token projection")
    ap.add_argument("--loops", type=int, default=8, help="loop count for --project (default 8)")
    ap.add_argument("--once", nargs="*", help="files read once per run (×1, e.g. startup.md)")
    ap.add_argument("--lens", choices=["apple", "generic"], default="apple",
                    help="stack lens to model (default apple, the heavier path)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    count_fn, method = _make_counter()
    if args.loaded_set:
        cmd_loaded_set(args, count_fn, method)
    elif args.project:
        cmd_project(args, count_fn, method)
    else:
        cmd_files(args, count_fn, method)
    return 0


if __name__ == "__main__":
    sys.exit(main())
