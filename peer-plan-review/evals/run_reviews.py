#!/usr/bin/env python3
"""Driver for the peer-plan-review efficacy harness.

Usage:
  python3 run_reviews.py baseline           # cross-family recall/precision/format
  python3 run_reviews.py microtest [reps]   # control-vs-treat wording reps (default 5)

Regenerates prompts, then runs the matrix via ../scripts/run_review.py in parallel
(cap 6). Outputs land in ./runs/<mode>/ (gitignored). Score with score.py.

Cost note: defaults to cheap/mid models (Haiku/Sonnet/Codex-mini) and effort=medium,
per the project's "cheapest model that proves the path" rule. Edit MATRIX to change.
"""
import subprocess, sys, pathlib, uuid, json
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = pathlib.Path(__file__).resolve().parent
SKILL = HERE.parent
RUNNER = SKILL / "scripts" / "run_review.py"
GEN = HERE / "_generated"
FIX = HERE / "fixtures" / "digest-plan.md"

# Each job: (label, reviewer, model, effort, prompt_basename, plan_file)
BASELINE = [
    ("std-sonnet",  "claude", "sonnet",        "medium", "baseline-standard.md",    FIX),
    ("std-codex",   "codex",  "gpt-5.4-mini",  "low",    "baseline-standard.md",    FIX),
    ("domain",      "claude", "sonnet",        "medium", "baseline-domain.md",      FIX),
    ("adversarial", "claude", "sonnet",        "medium", "baseline-adversarial.md", FIX),
]
# (battery, model)  — control+treat prompts are mt-<battery>-{control,treat}.md
MICRO = [("obs", "haiku"), ("ex", "haiku"), ("sev", "haiku"), ("f2", "sonnet"), ("f3", "sonnet")]


def cleanup_codex_homes(jobs):
    """Reclaim per-run CODEX_HOME dirs minted by codex reviewer jobs.

    Each codex job's CODEX_HOME holds a copy of ~/.codex/auth.json; run_review.py
    isolates one per run (see _common/session/codex_home.py) but never reclaims
    it itself — that's the caller's job once the review is done. No-op for jobs
    that never touched CODEX_HOME (gemini/claude reviewers, or a codex job that
    failed before minting a home).
    """
    sys.path.insert(0, str(SKILL / "scripts"))
    from _common.session.codex_home import cleanup_review_homes

    created = failed = 0
    for label, _reviewer, _model, _effort, _prompt, _plan, outdir in jobs:
        session_file = outdir / f"{label}-session.json"
        if session_file.exists():
            try:
                data = json.loads(session_file.read_text(encoding="utf-8"))
                if data.get("codex_home"):
                    created += 1
            except (OSError, json.JSONDecodeError):
                pass
        failed += cleanup_review_homes(str(outdir), label)
    reclaimed = max(created - failed, 0)
    tail = f", {failed} left for retry" if failed else ""
    print(f"[codex-home cleanup] reclaimed {reclaimed}/{created} codex home(s){tail}")


def run_job(label, reviewer, model, effort, prompt, plan, outdir):
    rid = "ev" + uuid.uuid4().hex[:6]
    out = outdir / f"{label}-review.md"
    cmd = [sys.executable, str(RUNNER),
           "--reviewer", reviewer, "--model", model, "--effort", effort, "--timeout", "400",
           "--plan-file", str(plan), "--prompt-file", str(GEN / prompt),
           "--output-file", str(out),
           "--session-file", str(outdir / f"{label}-session.json"),
           "--events-file", str(outdir / f"{label}-events.jsonl"),
           "--error-log", str(outdir / f"{label}-errors.jsonl"),
           "--review-id", rid]
    p = subprocess.run(cmd, capture_output=True, text=True)
    return (label, reviewer, model, p.returncode, out.exists() and out.stat().st_size > 0)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    subprocess.run([sys.executable, str(HERE / "build_prompts.py")], check=True)
    tempt = GEN / "_plan-tempt.md"

    jobs = []
    if mode == "baseline":
        outdir = HERE / "runs" / "baseline"; outdir.mkdir(parents=True, exist_ok=True)
        for j in BASELINE:
            jobs.append((*j[:4], j[4], j[5], outdir))
    elif mode == "microtest":
        reps = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        outdir = HERE / "runs" / "microtest"; outdir.mkdir(parents=True, exist_ok=True)
        for bat, model in MICRO:
            plan = tempt if bat == "f3" else FIX
            for arm in ("control", "treat"):
                for r in range(1, reps + 1):
                    jobs.append((f"{bat}-{arm}-{r}", "claude", model, "medium",
                                 f"mt-{bat}-{arm}.md", plan, outdir))
    else:
        sys.exit(f"unknown mode: {mode!r} (use 'baseline' or 'microtest')")

    print(f"[{mode}] running {len(jobs)} job(s), cap=6 ...")
    try:
        results = []
        with ThreadPoolExecutor(max_workers=6) as ex:
            futs = [ex.submit(run_job, *j) for j in jobs]
            for f in as_completed(futs):
                r = f.result(); results.append(r)
                print(f"  {r[0]:18s} {r[1]:7s}/{r[2]:13s} exit={r[3]} ok={r[4]}")
        ok = sum(1 for r in results if r[4])
        print(f"\n{mode}: ok={ok}/{len(results)}")
        for r in results:
            if not r[4]:
                print("  FAILED:", r[:3])
    finally:
        cleanup_codex_homes(jobs)


if __name__ == "__main__":
    main()
