#!/usr/bin/env python3
"""
run_quorum.py — Orchestrator for multi-provider quorum review.

Launches multiple reviewer instances (via peer-plan-review's run_review.py),
collects their verdicts, compiles the deliberation context for subsequent
rounds, and reports consensus status.

This script does NOT revise the plan — the host agent does that between
rounds. This script handles:
  1. Parsing the reviewer panel specification
  2. Launching reviewers (sequential or concurrent)
  3. Collecting and tallying verdicts
  4. Compiling deliberation context (all reviews) for next-round prompts
  5. Writing round summary with tally and consensus status
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import textwrap
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


# ---------------------------------------------------------------------------
# Quorum thresholds
# ---------------------------------------------------------------------------

THRESHOLDS = {
    "unanimous": lambda approved, total: approved == total,
    "super": lambda approved, total: approved >= total - 1,
    "majority": lambda approved, total: approved > total / 2,
}


def parse_reviewer_spec(spec):
    """Parse 'provider[:model]' into (provider, model_or_None).

    >>> parse_reviewer_spec("claude:sonnet")
    ('claude', 'sonnet')
    >>> parse_reviewer_spec("codex")
    ('codex', None)
    """
    parts = spec.split(":", 1)
    provider = parts[0].lower()
    model = parts[1] if len(parts) > 1 else None
    return provider, model


VALID_PROVIDERS = {"claude", "gemini", "codex", "copilot"}


def validate_panel(reviewers):
    """Validate the reviewer panel. Returns list of (provider, model) tuples."""
    panel = []
    for spec in reviewers:
        provider, model = parse_reviewer_spec(spec)
        if provider not in VALID_PROVIDERS:
            print(
                f"Error: unknown provider '{provider}'. "
                f"Valid: {', '.join(sorted(VALID_PROVIDERS))}",
                file=sys.stderr,
            )
            sys.exit(1)
        panel.append((provider, model))

    if len(panel) < 3:
        print(
            f"Error: quorum requires at least 3 reviewers, got {len(panel)}. "
            "Use /peer-plan-review for single-reviewer mode.",
            file=sys.stderr,
        )
        sys.exit(1)

    return panel


# ---------------------------------------------------------------------------
# Reviewer execution
# ---------------------------------------------------------------------------


def _resolve_run_review():
    """Locate peer-plan-review's run_review.py relative to this script."""
    this_dir = Path(__file__).resolve().parent
    # quorum-review/scripts/ -> peer-plan-review/scripts/
    candidate = this_dir.parent.parent / "peer-plan-review" / "scripts" / "run_review.py"
    if candidate.exists():
        return str(candidate)
    # Fallback: check PATH
    print(
        "Error: cannot locate peer-plan-review/scripts/run_review.py. "
        "Ensure peer-plan-review skill is installed alongside quorum-review.",
        file=sys.stderr,
    )
    sys.exit(1)


def run_single_reviewer(
    run_review_py,
    provider,
    model,
    plan_file,
    prompt_file,
    output_file,
    session_file,
    events_file,
    effort=None,
    resume=False,
    timeout=600,
):
    """Run a single reviewer via run_review.py. Returns exit code."""
    cmd = [
        sys.executable,
        run_review_py,
        "--reviewer", provider,
        "--plan-file", plan_file,
        "--prompt-file", prompt_file,
        "--output-file", output_file,
        "--session-file", session_file,
        "--events-file", events_file,
        "--timeout", str(timeout),
    ]
    if model:
        cmd.extend(["--model", model])
    if effort:
        cmd.extend(["--effort", effort])
    if resume:
        cmd.append("--resume")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout + 30,  # grace period beyond reviewer timeout
        )
        if result.stderr:
            print(f"[{provider}:{model or 'default'}] {result.stderr}", file=sys.stderr)
        return result.returncode
    except subprocess.TimeoutExpired:
        print(f"[{provider}:{model or 'default'}] orchestrator timeout", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[{provider}:{model or 'default'}] error: {e}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# Verdict parsing
# ---------------------------------------------------------------------------


def parse_verdict(review_file):
    """Parse VERDICT from the last non-empty line of review output.

    Returns 'APPROVED', 'REVISE', or None.
    """
    if not review_file or not Path(review_file).exists():
        return None
    try:
        with Path(review_file).open(encoding="utf-8") as f:
            lines = f.read().strip().splitlines()
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
            if line == "VERDICT: APPROVED":
                return "APPROVED"
            if line == "VERDICT: REVISE":
                return "REVISE"
            # Only check last non-empty line
            return None
    except OSError:
        return None


def read_review(review_file):
    """Read the full review text from a reviewer's output file."""
    if not review_file or not Path(review_file).exists():
        return ""
    try:
        with Path(review_file).open(encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def read_session_meta(session_file):
    """Read session metadata JSON."""
    if not session_file or not Path(session_file).exists():
        return {}
    try:
        with Path(session_file).open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


# ---------------------------------------------------------------------------
# Deliberation context compilation
# ---------------------------------------------------------------------------


def compile_deliberation(panel, quorum_id, tmpdir, round_num):
    """Compile all reviews from a round into a deliberation document.

    Returns the deliberation text and a list of (reviewer_label, verdict) tuples.
    """
    sections = []
    verdicts = []

    for idx, (provider, model) in enumerate(panel, 1):
        label = f"Reviewer {idx} ({provider}:{model or 'default'})"
        review_file = Path(tmpdir) / f"qr-{quorum_id}-r{idx}-review.md"
        session_file = Path(tmpdir) / f"qr-{quorum_id}-r{idx}-session.json"

        review_text = read_review(str(review_file))
        verdict = parse_verdict(str(review_file))
        meta = read_session_meta(str(session_file))

        actual_model = meta.get("model", model or "default")
        actual_effort = meta.get("effort", "default")

        verdict_str = verdict or "NO VERDICT"
        verdicts.append((label, verdict, actual_model, actual_effort))

        sections.append(
            f"--- {label} (model: {actual_model}, effort: {actual_effort}) "
            f"— VERDICT: {verdict_str} ---\n\n{review_text}"
        )

    deliberation_text = "\n\n".join(sections)
    return deliberation_text, verdicts


def write_deliberation_prompt(
    prompt_file,
    reviewer_index,
    total_reviewers,
    round_num,
    review_contract,
    deliberation_text,
    changes_summary,
    plan_text,
):
    """Write the deliberation prompt for a specific reviewer in rounds 2+."""
    content = textwrap.dedent(f"""\
        {review_contract}

        ## Panel Context

        You are reviewer {reviewer_index} of {total_reviewers} in a quorum review panel.
        This is round {round_num}. Below are ALL reviews from the previous round,
        including your own. Consider the other reviewers' points carefully.
        You may agree, disagree, or refine their feedback. The host has revised
        the plan based on the combined feedback.

        ## Reviews from Previous Round

        {deliberation_text}

        ## Changes Since Last Round (by HOST)

        {changes_summary}

        ## Updated Plan

        {plan_text}
    """)

    Path(prompt_file).write_text(content, encoding="utf-8")


def write_initial_prompt(
    prompt_file,
    reviewer_index,
    total_reviewers,
    review_contract,
    plan_text,
):
    """Write the initial review prompt for round 1."""
    content = textwrap.dedent(f"""\
        {review_contract}

        ## Panel Context

        You are reviewer {reviewer_index} of {total_reviewers} in a quorum review panel.
        Other reviewers are also evaluating this plan independently. In subsequent
        rounds you will see their feedback and can respond to it. For now, provide
        your independent assessment.

        ## Plan

        {plan_text}
    """)

    Path(prompt_file).write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Tally & consensus
# ---------------------------------------------------------------------------


def tally_verdicts(verdicts, threshold_name):
    """Compute consensus from a list of (label, verdict, model, effort) tuples.

    Returns dict with:
      - approved: list of labels that approved
      - revise: list of labels that voted revise
      - failed: list of labels with no verdict
      - total: total reviewers
      - threshold_met: bool
      - summary: human-readable tally string
    """
    approved = [v for v in verdicts if v[1] == "APPROVED"]
    revise = [v for v in verdicts if v[1] == "REVISE"]
    failed = [v for v in verdicts if v[1] is None]

    total = len(verdicts)
    n_approved = len(approved)
    threshold_fn = THRESHOLDS.get(threshold_name, THRESHOLDS["unanimous"])
    threshold_met = threshold_fn(n_approved, total)

    # Build threshold label
    if threshold_name == "unanimous":
        threshold_label = f"unanimous ({total}/{total})"
    elif threshold_name == "super":
        threshold_label = f"supermajority ({total - 1}/{total})"
    else:
        threshold_label = f"majority ({total // 2 + 1}/{total})"

    lines = [
        f"- APPROVED: {n_approved}/{total}"
        + (f" ({', '.join(v[0] for v in approved)})" if approved else ""),
        f"- REVISE: {len(revise)}/{total}"
        + (f" ({', '.join(v[0] for v in revise)})" if revise else ""),
    ]
    if failed:
        lines.append(
            f"- NO VERDICT: {len(failed)}/{total}"
            f" ({', '.join(v[0] for v in failed)})"
        )
    lines.append(f"- Threshold: {threshold_label}")
    lines.append(f"- Status: {'CONSENSUS REACHED' if threshold_met else 'NOT MET'}")

    return {
        "approved": approved,
        "revise": revise,
        "failed": failed,
        "total": total,
        "threshold_met": threshold_met,
        "summary": "\n".join(lines),
    }


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------


def parse_args():
    p = argparse.ArgumentParser(description="Quorum review orchestrator")
    p.add_argument(
        "--reviewers",
        required=True,
        help="Comma-separated reviewer specs (e.g., 'claude:sonnet,gemini:pro,codex')",
    )
    p.add_argument("--plan-file", required=True, help="Path to plan markdown file")
    p.add_argument("--quorum-id", required=True, help="Unique quorum session ID")
    p.add_argument("--round", type=int, required=True, help="Current round number (1-indexed)")
    p.add_argument(
        "--threshold",
        default="unanimous",
        choices=list(THRESHOLDS.keys()),
        help="Consensus threshold (default: unanimous)",
    )
    p.add_argument("--effort", default=None, help="Effort level for all reviewers")
    p.add_argument("--timeout", type=int, default=600, help="Per-reviewer timeout in seconds")
    p.add_argument("--tmpdir", default=None, help="Temp directory (default: system temp)")
    p.add_argument(
        "--deliberation-file",
        default=None,
        help="Path to write compiled deliberation context",
    )
    p.add_argument(
        "--changes-summary",
        default=None,
        help="Path to file containing changes-since-last-round bullet list",
    )
    p.add_argument(
        "--sequential",
        action="store_true",
        help="Run reviewers sequentially instead of in parallel",
    )
    p.add_argument(
        "--tally-file",
        default=None,
        help="Path to write JSON tally results",
    )
    return p.parse_args()


def main():
    args = parse_args()

    # Parse and validate panel
    reviewer_specs = [s.strip() for s in args.reviewers.split(",") if s.strip()]
    panel = validate_panel(reviewer_specs)
    round_num = args.round

    # Resolve paths
    run_review_py = _resolve_run_review()
    tmpdir = args.tmpdir or os.environ.get("TMPDIR") or "/tmp"
    quorum_id = args.quorum_id
    plan_file = args.plan_file

    # Read plan text for prompt generation
    plan_text = Path(plan_file).read_text(encoding="utf-8")

    # Standard review contract
    review_contract = textwrap.dedent("""\
        ## Review Contract

        You are reviewing a plan as part of a multi-reviewer quorum panel.
        Provide thorough, constructive feedback on the plan.

        Your review MUST end with a verdict on the LAST non-empty line:
        - `VERDICT: APPROVED` if the plan is ready to execute as-is
        - `VERDICT: REVISE` if changes are needed before execution

        The verdict line must be EXACTLY one of these two strings, nothing else.
    """)

    # Read deliberation context from prior round (for rounds 2+)
    deliberation_text = ""
    changes_summary = "N/A (first round)"
    if round_num > 1:
        delib_file = args.deliberation_file
        if delib_file and Path(delib_file).exists():
            deliberation_text = Path(delib_file).read_text(encoding="utf-8")
        if args.changes_summary and Path(args.changes_summary).exists():
            changes_summary = Path(args.changes_summary).read_text(encoding="utf-8")

    # Generate per-reviewer prompts
    resume = round_num > 1
    for idx, (provider, model) in enumerate(panel, 1):
        prompt_file = Path(tmpdir) / f"qr-{quorum_id}-r{idx}-prompt.md"
        if round_num == 1:
            write_initial_prompt(
                str(prompt_file), idx, len(panel), review_contract, plan_text
            )
        else:
            write_deliberation_prompt(
                str(prompt_file),
                idx,
                len(panel),
                round_num,
                review_contract,
                deliberation_text,
                changes_summary,
                plan_text,
            )

    # Execute reviewers
    results = {}  # idx -> exit_code

    def _run_reviewer(idx, provider, model):
        prompt_file = str(Path(tmpdir) / f"qr-{quorum_id}-r{idx}-prompt.md")
        output_file = str(Path(tmpdir) / f"qr-{quorum_id}-r{idx}-review.md")
        session_file = str(Path(tmpdir) / f"qr-{quorum_id}-r{idx}-session.json")
        events_file = str(Path(tmpdir) / f"qr-{quorum_id}-r{idx}-events.jsonl")

        rc = run_single_reviewer(
            run_review_py,
            provider,
            model,
            plan_file,
            prompt_file,
            output_file,
            session_file,
            events_file,
            effort=args.effort,
            resume=resume,
            timeout=args.timeout,
        )
        return idx, rc

    if args.sequential:
        for idx, (provider, model) in enumerate(panel, 1):
            i, rc = _run_reviewer(idx, provider, model)
            results[i] = rc
            label = f"{provider}:{model or 'default'}"
            status = "OK" if rc == 0 else f"FAILED (exit {rc})"
            print(f"[Round {round_num}] {label}: {status}", file=sys.stderr)
    else:
        with ThreadPoolExecutor(max_workers=len(panel)) as pool:
            futures = {
                pool.submit(_run_reviewer, idx, provider, model): (idx, provider, model)
                for idx, (provider, model) in enumerate(panel, 1)
            }
            for future in as_completed(futures):
                idx, provider, model = futures[future]
                label = f"{provider}:{model or 'default'}"
                try:
                    i, rc = future.result()
                    results[i] = rc
                    status = "OK" if rc == 0 else f"FAILED (exit {rc})"
                    print(f"[Round {round_num}] {label}: {status}", file=sys.stderr)
                except Exception as e:
                    results[idx] = 1
                    print(f"[Round {round_num}] {label}: EXCEPTION: {e}", file=sys.stderr)

    # Compile deliberation and tally
    deliberation_text, verdicts = compile_deliberation(panel, quorum_id, tmpdir, round_num)
    tally = tally_verdicts(verdicts, args.threshold)

    # Write deliberation file for next round
    delib_out = args.deliberation_file or str(
        Path(tmpdir) / f"qr-{quorum_id}-deliberation.md"
    )
    Path(delib_out).write_text(deliberation_text, encoding="utf-8")

    # Write tally as JSON
    tally_data = {
        "round": round_num,
        "threshold": args.threshold,
        "threshold_met": tally["threshold_met"],
        "approved_count": len(tally["approved"]),
        "revise_count": len(tally["revise"]),
        "failed_count": len(tally["failed"]),
        "total": tally["total"],
        "reviewers": [
            {
                "label": v[0],
                "verdict": v[1],
                "model": v[2],
                "effort": v[3],
            }
            for v in verdicts
        ],
        "exit_codes": results,
    }
    tally_file = args.tally_file or str(Path(tmpdir) / f"qr-{quorum_id}-tally.json")
    Path(tally_file).write_text(json.dumps(tally_data, indent=2), encoding="utf-8")

    # Print summary to stdout for host agent consumption
    print(f"\n## Quorum Review — Round {round_num} Tally\n")
    print(tally["summary"])
    print(f"\nDeliberation context written to: {delib_out}")
    print(f"Tally written to: {tally_file}")

    # Exit 0 if consensus, 2 if not met (distinct from error exit 1)
    if tally["threshold_met"]:
        print("\nCONSENSUS: REACHED")
        sys.exit(0)
    else:
        print("\nCONSENSUS: NOT MET")
        sys.exit(2)


if __name__ == "__main__":
    main()
