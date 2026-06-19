# WAIVER: module-size — top-of-graph driver (main + round-loop + ledger
#   build + early-exit + tally + verification dispatch + deliberation +
#   compressed-context + reviewer fan-out). The 7-module shape fixed by
#   the Phase C plan keeps these together; splitting would synthesize a
#   module without a clear distinct responsibility.
"""quorum.orchestrator — round-loop driver, reviewer dispatch, derived verdict.

Top of the dependency graph: pulls from every other ``quorum.*`` module to
drive the per-round flow — locate ``run_review.py``, generate the per-
reviewer prompts via ``quorum.prompts``, fan out reviewer subprocesses
(sequential or threaded), assemble the anonymous deliberation context,
build/refresh the issue ledger via ``quorum.ledger`` + ``quorum.merge``,
optionally run the external verifier via ``quorum.verification``, then
derive the artifact verdict and emit the tally JSON.

``main()`` resolves ``run_single_reviewer`` through the public shim
(``run_quorum``) at call time so that
``unittest.mock.patch.object(run_quorum, "run_single_reviewer", ...)`` in
the test suite actually intercepts the call.
"""

import copy
import subprocess
import sys
import tempfile
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from quorum.cli import (
    MIN_QUORUM_SIZE,
    THRESHOLDS,
    _resolve_verifier_spec,
    parse_args,
    validate_panel,
)
from quorum.parsing import (
    parse_cross_critique,
    parse_structured_review,
    parse_verdict,
    read_review,
    read_session_meta,
    _normalize_text,
)
from quorum.ledger import (
    _as_list,
    _empty_ledger,
    _issue_dispute_count,
    _issue_is_invalidated,
    _issue_severity,
    _issue_status,
    _issue_summary,
    _issue_support_count,
    _make_issue,
    _refresh_issue,
    load_ledger,
    save_ledger,
)
from quorum.merge import apply_merge_pipeline
from quorum.verification import (
    _sync_verification_state,
    generate_verification_prompts,
    parse_verification_response,
)
from quorum.prompts import (
    CROSS_CRITIQUE_INSTRUCTIONS,
    _artifact_heading_for_mode,
    _review_contract_for_mode,
    _role_for_mode,
    format_ledger_summary,
    load_review_md,
    write_cross_critique_prompt,
    write_initial_prompt,
)


EXIT_APPROVED = 0
EXIT_ERROR = 1
EXIT_REVISE = 2
EXIT_INDETERMINATE = 3


# ---------------------------------------------------------------------------
# Reviewer execution
# ---------------------------------------------------------------------------


def _resolve_run_review():
    """Locate run_review.py in this skill's scripts/ directory."""
    # __file__ here is .../scripts/quorum/orchestrator.py — go up one extra
    # level so we land in scripts/ where run_review.py lives.
    scripts_dir = Path(__file__).resolve().parent.parent
    candidate = scripts_dir / "run_review.py"
    if candidate.exists():
        return str(candidate)
    # Not found — exit with guidance
    print(
        "Error: cannot locate scripts/run_review.py. "
        "Ensure run_review.py is present in the quorum-review scripts/ directory.",
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
    verification_mode=False,
    codex_home_manifest=None,
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
    # Review-scoped manifest of per-run Codex homes (concurrency isolation +
    # terminal cleanup). Every reviewer + verifier in a review shares one path.
    if codex_home_manifest:
        cmd.extend(["--codex-home-manifest", codex_home_manifest])
    if model:
        cmd.extend(["--model", model])
    if effort:
        cmd.extend(["--effort", effort])
    if resume:
        cmd.append("--resume")
    if verification_mode:
        cmd.append("--verification-mode")

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
# Issue ledger build (round dispatch)
# ---------------------------------------------------------------------------


def build_issue_ledger(panel, quorum_id, tmpdir, round_num, prev_ledger=None):
    """Build/update issue ledger from structured reviews.

    Round 1: Extract issues from each reviewer, assign canonical IDs.
    Rounds 2+: Parse cross-critique responses, update agreement counts,
               add new issues from [B-NEW]/[N-NEW] tags.

    Returns updated ledger dict.
    """
    # Lazy import keeps orchestrator import-light when only build_issue_ledger
    # is reached without the rest of main()'s deps.
    from quorum.ledger import _migrate_ledger

    ledger = _migrate_ledger(prev_ledger) if prev_ledger else _empty_ledger()

    if round_num == 1:
        blocking_count = 0
        nb_count = 0
        approved_count = 0

        for idx, (_provider, _model) in enumerate(panel, 1):
            review_file = str(Path(tmpdir) / f"qr-{quorum_id}-r{idx}-review.md")
            parsed = parse_structured_review(review_file)
            category = ", ".join(parsed["scope"]) if parsed["scope"] else "general"

            for issue in parsed["blocking"]:
                canonical_id = f"BLK-{ledger['next_blk_id']:03d}"
                ledger["next_blk_id"] += 1
                ledger["issues"].append(
                    _make_issue(
                        canonical_id,
                        "blocking",
                        round_num,
                        idx,
                        issue["id"],
                        issue["text"],
                        anchor=issue.get("anchor"),
                        category=category,
                        confidence=issue.get("confidence"),
                    )
                )
                blocking_count += 1

            for issue in parsed["non_blocking"]:
                canonical_id = f"NB-{ledger['next_nb_id']:03d}"
                ledger["next_nb_id"] += 1
                ledger["issues"].append(
                    _make_issue(
                        canonical_id,
                        "non_blocking",
                        round_num,
                        idx,
                        issue["id"],
                        issue["text"],
                        anchor=issue.get("anchor"),
                        category=category,
                    )
                )
                nb_count += 1

            if parsed["verdict"] == "APPROVED":
                approved_count += 1

        ledger["rounds"][str(round_num)] = {
            "reviewer_count": len(panel),
            "blocking_open": blocking_count,
            "nb_open": nb_count,
            "approved_count": approved_count,
        }

    else:
        approved_count = 0
        issue_map = {issue["id"]: issue for issue in ledger["issues"]}

        for idx, (_provider, _model) in enumerate(panel, 1):
            review_file = str(Path(tmpdir) / f"qr-{quorum_id}-r{idx}-review.md")
            critique = parse_cross_critique(review_file)
            parsed = parse_structured_review(review_file)
            category = ", ".join(parsed["scope"]) if parsed["scope"] else "general"

            for issue_id in critique["agrees"]:
                if issue_id in issue_map:
                    issue = issue_map[issue_id]
                    if idx not in _as_list(issue["adjudication"].get("proposed_by")) and idx not in issue["adjudication"]["endorsed_by"]:
                        issue["adjudication"]["endorsed_by"].append(idx)
                        _refresh_issue(issue)

            for entry in critique["disagrees"]:
                issue_id = entry["id"]
                if issue_id in issue_map:
                    issue = issue_map[issue_id]
                    if idx not in issue["adjudication"]["disputed_by"]:
                        issue["adjudication"]["disputed_by"].append(idx)
                        _refresh_issue(issue)

            for entry in critique["refines"]:
                issue_id = entry["id"]
                if issue_id in issue_map:
                    issue = issue_map[issue_id]
                    if idx not in _as_list(issue["adjudication"].get("proposed_by")) and idx not in issue["adjudication"]["refined_by"]:
                        issue["adjudication"]["refined_by"].append(idx)
                        _refresh_issue(issue)

            for text in critique["new_blocking"]:
                canonical_id = f"BLK-{ledger['next_blk_id']:03d}"
                ledger["next_blk_id"] += 1
                new_issue = _make_issue(
                    canonical_id,
                    "blocking",
                    round_num,
                    idx,
                    "B-NEW",
                    text,
                    category=category,
                )
                ledger["issues"].append(new_issue)
                issue_map[canonical_id] = new_issue

            for text in critique["new_non_blocking"]:
                canonical_id = f"NB-{ledger['next_nb_id']:03d}"
                ledger["next_nb_id"] += 1
                new_issue = _make_issue(
                    canonical_id,
                    "non_blocking",
                    round_num,
                    idx,
                    "N-NEW",
                    text,
                    category=category,
                )
                ledger["issues"].append(new_issue)
                issue_map[canonical_id] = new_issue

            existing_texts = {
                _normalize_text(_issue_summary(i))
                for i in ledger["issues"]
                if _issue_summary(i)
            }

            if parsed.get("has_blocking_section"):
                for section_issue in parsed["blocking"]:
                    text = section_issue["text"].strip()
                    normalized = _normalize_text(text)
                    if normalized not in existing_texts:
                        canonical_id = f"BLK-{ledger['next_blk_id']:03d}"
                        ledger["next_blk_id"] += 1
                        new_issue = _make_issue(
                            canonical_id,
                            "blocking",
                            round_num,
                            idx,
                            "section-scan",
                            text,
                            anchor=section_issue.get("anchor"),
                            category=category,
                            confidence=section_issue.get("confidence"),
                        )
                        ledger["issues"].append(new_issue)
                        issue_map[canonical_id] = new_issue
                        existing_texts.add(normalized)

            if parsed.get("has_non_blocking_section"):
                for section_issue in parsed["non_blocking"]:
                    text = section_issue["text"].strip()
                    normalized = _normalize_text(text)
                    if normalized not in existing_texts:
                        canonical_id = f"NB-{ledger['next_nb_id']:03d}"
                        ledger["next_nb_id"] += 1
                        new_issue = _make_issue(
                            canonical_id,
                            "non_blocking",
                            round_num,
                            idx,
                            "section-scan",
                            text,
                            anchor=section_issue.get("anchor"),
                            category=category,
                        )
                        ledger["issues"].append(new_issue)
                        issue_map[canonical_id] = new_issue
                        existing_texts.add(normalized)

            if parsed["verdict"] == "APPROVED":
                approved_count += 1

        ledger["rounds"][str(round_num)] = {
            "reviewer_count": len(panel),
            "blocking_open": sum(
                1 for i in ledger["issues"]
                if _issue_severity(i) == "blocking" and _issue_status(i) == "open"
            ),
            "nb_open": sum(
                1 for i in ledger["issues"]
                if _issue_severity(i) == "non_blocking" and _issue_status(i) == "open"
            ),
            "approved_count": approved_count,
        }

    return ledger


# ---------------------------------------------------------------------------
# Derived verdict (v3)
# ---------------------------------------------------------------------------


def derive_verdict(ledger, threshold_name, total_reviewers):
    """Derive artifact verdict from surviving blocking issues.

    A blocking issue 'survives' if its support_count meets the configured
    threshold relative to total_reviewers.

    Returns (verdict, surviving_issues, dropped_issues) where:
      - verdict: "APPROVED" or "REVISE"
      - surviving_issues: list of issue dicts that survive
      - dropped_issues: list of issue dicts that don't meet threshold
    """
    threshold_fn = THRESHOLDS.get(threshold_name, THRESHOLDS["super"])

    open_blockers = [
        i for i in ledger["issues"]
        if _issue_severity(i) == "blocking" and _issue_status(i) == "open" and not _issue_is_invalidated(i)
    ]

    surviving = []
    dropped = []

    for issue in open_blockers:
        # An issue "survives" if its support count meets the threshold
        # We invert the threshold: instead of "N approved out of total",
        # we check "support_count supporters out of total"
        if threshold_fn(_issue_support_count(issue), total_reviewers):
            surviving.append(issue)
        else:
            dropped.append(issue)

    verdict = "REVISE" if surviving else "APPROVED"
    return verdict, surviving, dropped


def format_issue_consensus(ledger, threshold_name, total_reviewers):
    """Format issue consensus for display.

    Returns human-readable markdown showing which issues survive.
    """
    verdict, surviving, dropped = derive_verdict(ledger, threshold_name, total_reviewers)

    lines = ["### Issue Consensus\n"]

    if surviving:
        for issue in surviving:
            lines.append(
                f"- {issue['id']} \"{_issue_summary(issue)}\": "
                f"support {_issue_support_count(issue)}/{total_reviewers} "
                f"— SURVIVES"
            )
    if dropped:
        for issue in dropped:
            lines.append(
                f"- {issue['id']} \"{_issue_summary(issue)}\": "
                f"support {_issue_support_count(issue)}/{total_reviewers} "
                f"— DROPPED"
            )

    # Non-blocking issues (informational)
    open_nb = [
        i for i in ledger["issues"]
        if _issue_severity(i) == "non_blocking" and _issue_status(i) == "open"
    ]
    for issue in open_nb:
        lines.append(
            f"- {issue['id']} \"{_issue_summary(issue)}\": "
            f"support {_issue_support_count(issue)}/{total_reviewers} "
            f"— NON-BLOCKING"
        )

    surviving_count = len(surviving)
    lines.append(
        f"\n### Derived Verdict: {verdict} "
        f"({surviving_count} blocking issue(s) survive {threshold_name} threshold)"
    )

    return "\n".join(lines)


def _is_unanimous(ledger, issue_id, total):
    """Check if a blocker has unanimous support (support_count >= total).

    Used to skip verification for unanimously-endorsed blockers — these are
    high-probability true positives that don't need additional validation.
    """
    issue = next((i for i in ledger["issues"] if i["id"] == issue_id), None)
    return issue is not None and _issue_support_count(issue) >= total and not _issue_is_invalidated(issue)


def should_exit_early(ledger, threshold_name, total_reviewers):
    """Check whether further deliberation rounds would be mathematically futile.

    Returns (should_exit, reason) where:
      - should_exit: True if no further rounds can change the outcome
      - reason: human-readable explanation (empty string if should_exit is False)

    Checks:
    1. No open blockers remain → verdict is APPROVED, stop
    2. No blockers meet threshold → verdict would be APPROVED, stop
    3. All surviving blockers at max support → more rounds won't change, stop
    """
    open_blockers = [
        i for i in ledger["issues"]
        if _issue_severity(i) == "blocking" and _issue_status(i) == "open" and not _issue_is_invalidated(i)
    ]

    if not open_blockers:
        return True, "no open blockers remain"

    threshold_fn = THRESHOLDS.get(threshold_name, THRESHOLDS["super"])
    surviving = [i for i in open_blockers if threshold_fn(_issue_support_count(i), total_reviewers)]

    if not surviving:
        return True, "no blockers meet threshold — verdict would be APPROVED"

    all_at_max = all(_issue_support_count(i) >= total_reviewers for i in surviving)
    if all_at_max:
        return True, "all surviving blockers at maximum support — further rounds cannot change outcome"

    return False, ""


# ---------------------------------------------------------------------------
# Deliberation context compilation (v2 — always anonymous)
# ---------------------------------------------------------------------------


def compile_deliberation(panel, quorum_id, tmpdir, round_num):
    """Compile all reviews from a round into a deliberation document.

    All deliberation context is ANONYMOUS — reviewers are labeled as
    Reviewer A, B, C, etc. with no provider/model information. This
    prevents prestige bias from anchoring convergence.

    Returns (deliberation_text, verdicts, reviewer_map) where:
      - deliberation_text: anonymous markdown for prompts
      - verdicts: list of (anon_label, verdict, actual_model, actual_effort)
      - reviewer_map: dict mapping anon labels to true identities
    """
    sections = []
    verdicts = []
    reviewer_map = {}

    for idx, (provider, model) in enumerate(panel, 1):
        anon_label = f"Reviewer {chr(64 + idx)}"  # A, B, C, ...
        review_file = Path(tmpdir) / f"qr-{quorum_id}-r{idx}-review.md"
        session_file = Path(tmpdir) / f"qr-{quorum_id}-r{idx}-session.json"

        review_text = read_review(str(review_file))
        verdict = parse_verdict(str(review_file))
        meta = read_session_meta(str(session_file))

        actual_model = meta.get("model", model or "default")
        actual_effort = meta.get("effort", "default")

        verdict_str = verdict or "NO VERDICT"
        verdicts.append((anon_label, verdict, actual_model, actual_effort))

        reviewer_map[anon_label] = {
            "provider": provider,
            "model": model,
            "actual_model": actual_model,
            "actual_effort": actual_effort,
            "idx": idx,
        }

        # Anonymous section header — no model/effort info
        sections.append(
            f"--- {anon_label} — VERDICT: {verdict_str} ---\n\n{review_text}"
        )

    deliberation_text = "\n\n".join(sections)
    return deliberation_text, verdicts, reviewer_map


# ---------------------------------------------------------------------------
# Context compression (v2)
# ---------------------------------------------------------------------------


def compile_compressed_context(ledger, panel, quorum_id, tmpdir, round_num,
                               blind_mode=False):
    """Build compressed context for rounds 3+.

    Instead of full prose, carries forward:
    1. Issue ledger table (open issues only, with agreement counts)
    2. Per-reviewer: only their issue lists + verdict (not full prose)

    When blind_mode=True, omits Support and Disputes columns to prevent
    conformity anchoring in later rounds.

    Returns markdown string.
    """
    lines = ["## Open Issue Ledger\n"]

    open_issues = [i for i in ledger["issues"] if _issue_status(i) == "open"]
    if open_issues:
        if blind_mode:
            lines.append("| ID | Severity | Description |")
            lines.append("|-----|----------|-------------|")
            for issue in open_issues:
                lines.append(
                    f"| {issue['id']} | {_issue_severity(issue)} | "
                    f"{_issue_summary(issue)[:60]} |"
                )
        else:
            lines.append("| ID | Severity | Description | Support | Disputes |")
            lines.append("|-----|----------|-------------|---------|----------|")
            for issue in open_issues:
                lines.append(
                    f"| {issue['id']} | {_issue_severity(issue)} | "
                    f"{_issue_summary(issue)[:60]} | "
                    f"{_issue_support_count(issue)} | {_issue_dispute_count(issue)} |"
                )
    else:
        lines.append("No open issues remaining.")

    lines.append("\n## Prior Round Issue Lists (condensed)\n")

    for idx, (_provider, _model) in enumerate(panel, 1):
        anon_label = f"Reviewer {chr(64 + idx)}"
        review_file = Path(tmpdir) / f"qr-{quorum_id}-r{idx}-review.md"
        parsed = parse_structured_review(str(review_file))

        lines.append(f"### {anon_label} — VERDICT: {parsed['verdict'] or 'NO VERDICT'}")
        if parsed["blocking"]:
            lines.append("**Blocking:**")
            for issue in parsed["blocking"]:
                lines.append(f"- [{issue['id']}] {issue['text']}")
        if parsed["non_blocking"]:
            lines.append("**Non-blocking:**")
            for issue in parsed["non_blocking"]:
                lines.append(f"- [{issue['id']}] {issue['text']}")
        if not parsed["blocking"] and not parsed["non_blocking"]:
            lines.append("(No structured issues found)")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tally & consensus (v2 — advisory verdicts + derived verdict)
# ---------------------------------------------------------------------------


def tally_verdicts(verdicts, threshold_name, original_panel_size=None,
                   active_panel_size=None):
    """Compute advisory tally from a list of (label, verdict, model, effort) tuples.

    In v2, this tally is ADVISORY — the authoritative verdict comes from
    derive_verdict() based on surviving blocking issues.

    Returns dict with:
      - approved: list of verdict tuples that approved
      - revise: list of verdict tuples that voted revise
      - failed: list of verdict tuples with no verdict
      - total: active reviewers
      - original_panel_size: original panel before failures
      - active_panel_size: surviving panel after failure policy
      - threshold_met: bool (advisory)
      - summary: human-readable tally string
    """
    approved = [v for v in verdicts if v[1] == "APPROVED"]
    revise = [v for v in verdicts if v[1] == "REVISE"]
    failed = [v for v in verdicts if v[1] is None]

    total = len(verdicts)
    n_approved = len(approved)
    threshold_fn = THRESHOLDS.get(threshold_name, THRESHOLDS["super"])
    threshold_met = threshold_fn(n_approved, total)

    orig = original_panel_size if original_panel_size is not None else total
    active = active_panel_size if active_panel_size is not None else total

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
    if orig != active:
        lines.append(f"- Panel: {active} active of {orig} original")
    lines.append(
        f"- Advisory status: "
        f"{'CONSENSUS REACHED' if threshold_met else 'NOT MET'}"
        f" (advisory — derived verdict from issue ledger is authoritative)"
    )

    return {
        "approved": approved,
        "revise": revise,
        "failed": failed,
        "total": total,
        "original_panel_size": orig,
        "active_panel_size": active,
        "threshold_met": threshold_met,
        "summary": "\n".join(lines),
    }


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------


def main():
    # Resolve `run_single_reviewer` through the public shim at call time so
    # tests that ``patch.object(run_quorum, "run_single_reviewer", ...)``
    # intercept the call (a direct module-local reference would bypass the
    # patch). The shim is already in ``sys.modules`` whether main() was
    # invoked via the shim or directly through `python -m quorum.orchestrator`.
    import run_quorum  # noqa: WPS433 — intentional late import

    args = parse_args()

    # Parse and validate panel
    reviewer_specs = [s.strip() for s in args.reviewers.split(",") if s.strip()]
    panel = validate_panel(reviewer_specs)
    round_num = args.round
    original_panel_size = len(panel)

    # Resolve paths
    run_review_py = _resolve_run_review()
    tmpdir = args.tmpdir or tempfile.gettempdir()
    quorum_id = args.quorum_id
    plan_file = args.plan_file

    # Validate plan file exists
    if not Path(plan_file).exists():
        print(f"Error: --plan-file not found: {plan_file}", file=sys.stderr)
        sys.exit(1)

    # Read artifact text for prompt generation (plan/spec or code diff)
    artifact_text = Path(plan_file).read_text(encoding="utf-8")
    plan_text = artifact_text
    review_contract = _review_contract_for_mode(args.mode)
    artifact_heading = _artifact_heading_for_mode(args.mode)

    # Load REVIEW.md rubric if present
    rubric_text = load_review_md()

    # Load issue ledger (for rounds 2+)
    ledger_file = args.ledger_file or str(
        Path(tmpdir) / f"qr-{quorum_id}-ledger.json"
    )
    ledger = load_ledger(ledger_file) if round_num > 1 else _empty_ledger()

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
    for idx, (_provider, _model) in enumerate(panel, 1):
        prompt_file = Path(tmpdir) / f"qr-{quorum_id}-r{idx}-prompt.md"
        role_label = _role_for_mode(args.mode, idx)
        if round_num == 1:
            write_initial_prompt(
                str(prompt_file), idx, len(panel), review_contract, plan_text,
                rubric_text=rubric_text,
                mode=args.mode,
                role_label=role_label,
                artifact_heading=artifact_heading,
            )
        elif round_num == 2:
            # Round 2: full anonymous prose + cross-critique instructions
            write_cross_critique_prompt(
                str(prompt_file),
                idx,
                len(panel),
                round_num,
                review_contract,
                CROSS_CRITIQUE_INSTRUCTIONS,
                deliberation_text,
                format_ledger_summary(ledger),
                changes_summary,
                plan_text,
                mode=args.mode,
                role_label=role_label,
                artifact_heading=artifact_heading,
            )
        else:
            # Rounds 3+: compressed context + cross-critique instructions
            # blind_mode=True strips support/dispute counts to prevent
            # conformity anchoring in later rounds
            compressed = compile_compressed_context(
                ledger, panel, quorum_id, tmpdir, round_num,
                blind_mode=True,
            )
            write_cross_critique_prompt(
                str(prompt_file),
                idx,
                len(panel),
                round_num,
                review_contract,
                CROSS_CRITIQUE_INSTRUCTIONS,
                compressed,
                format_ledger_summary(ledger, blind_mode=True),
                changes_summary,
                plan_text,
                mode=args.mode,
                role_label=role_label,
                artifact_heading=artifact_heading,
            )

    # Execute reviewers
    results = {}  # idx -> exit_code

    def _run_reviewer(idx, provider, model):
        prompt_file = str(Path(tmpdir) / f"qr-{quorum_id}-r{idx}-prompt.md")
        output_file = str(Path(tmpdir) / f"qr-{quorum_id}-r{idx}-review.md")
        session_file = str(Path(tmpdir) / f"qr-{quorum_id}-r{idx}-session.json")
        events_file = str(Path(tmpdir) / f"qr-{quorum_id}-r{idx}-events.jsonl")

        rc = run_quorum.run_single_reviewer(
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
            codex_home_manifest=str(Path(tmpdir) / f"qr-{quorum_id}-codex-homes.list"),
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

    # Apply failure policy
    failed_reviewers = [idx for idx, rc in results.items() if rc != 0]
    active_panel = panel
    active_panel_size = len(panel)

    if failed_reviewers:
        if args.on_failure == "fail-closed":
            print(
                f"FAIL-CLOSED: {len(failed_reviewers)} reviewer(s) failed. Aborting.",
                file=sys.stderr,
            )
            sys.exit(1)
        elif args.on_failure == "shrink-quorum":
            surviving = len(panel) - len(failed_reviewers)
            if surviving < MIN_QUORUM_SIZE:
                print(
                    f"FAIL-CLOSED: only {surviving} reviewer(s) survived, "
                    f"minimum is {MIN_QUORUM_SIZE}. Aborting.",
                    file=sys.stderr,
                )
                sys.exit(1)
            # Build surviving panel (preserve order)
            active_panel = [
                (provider, model)
                for idx, (provider, model) in enumerate(panel, 1)
                if idx not in failed_reviewers
            ]
            active_panel_size = len(active_panel)
            print(
                f"SHRINK-QUORUM: panel reduced from {original_panel_size} "
                f"to {active_panel_size}",
                file=sys.stderr,
            )
        # fail-open: continue with original panel size as threshold denominator

    # Compile deliberation (always anonymous) and tally
    deliberation_text, verdicts, reviewer_map = compile_deliberation(
        panel, quorum_id, tmpdir, round_num
    )

    # For shrink-quorum, filter verdicts to active panel only
    if args.on_failure == "shrink-quorum" and failed_reviewers:
        verdicts = [
            v for v in verdicts
            if reviewer_map[v[0]]["idx"] not in failed_reviewers
        ]

    tally = tally_verdicts(
        verdicts, args.threshold,
        original_panel_size=original_panel_size,
        active_panel_size=active_panel_size,
    )

    # Build/update issue ledger
    ledger = build_issue_ledger(panel, quorum_id, tmpdir, round_num, ledger)
    verdict_ledger = copy.deepcopy(ledger) if round_num == 1 else ledger
    merge_result = apply_merge_pipeline(ledger, quorum_id, tmpdir, round_num)
    save_ledger(ledger_file, ledger)

    # Verification stage: validate surviving blockers with an external verifier
    verifier_spec = None
    if not args.skip_verification:
        # Derive current verdict to find surviving blockers
        _v_verdict, _v_surviving, _v_dropped = derive_verdict(
            verdict_ledger, args.threshold, active_panel_size
        )
        if _v_surviving:
            verification_prompts = generate_verification_prompts(
                verdict_ledger, artifact_text, args.threshold, active_panel_size, mode=args.mode
            )
            if verification_prompts:
                v_provider, v_model = _resolve_verifier_spec(active_panel, args.verifier)
                verifier_spec = {"provider": v_provider, "model": v_model}
                for vp in verification_prompts:
                    v_prompt_file = str(
                        Path(tmpdir) / f"qr-{quorum_id}-verify-{vp['issue_id']}-prompt.md"
                    )
                    v_output_file = str(
                        Path(tmpdir) / f"qr-{quorum_id}-verify-{vp['issue_id']}-review.md"
                    )
                    v_session_file = str(
                        Path(tmpdir) / f"qr-{quorum_id}-verify-{vp['issue_id']}-session.json"
                    )
                    v_events_file = str(
                        Path(tmpdir) / f"qr-{quorum_id}-verify-{vp['issue_id']}-events.jsonl"
                    )
                    # Write verification prompt
                    Path(v_prompt_file).write_text(vp["prompt"], encoding="utf-8")
                    # Run verifier
                    v_rc = run_quorum.run_single_reviewer(
                        run_review_py,
                        v_provider,
                        v_model,
                        plan_file,
                        v_prompt_file,
                        v_output_file,
                        v_session_file,
                        v_events_file,
                        effort=args.effort,
                        resume=False,
                        timeout=args.timeout,
                        verification_mode=True,
                        codex_home_manifest=str(Path(tmpdir) / f"qr-{quorum_id}-codex-homes.list"),
                    )
                    if v_rc == 0:
                        v_results = parse_verification_response(v_output_file)
                        for issue_id, status in v_results.items():
                            for issue in ledger["issues"]:
                                if issue["id"] != issue_id:
                                    continue
                                issue["verification"]["status"] = status.lower()
                                issue["verification"]["verified_by"] = {
                                    "provider": v_provider,
                                    "model": v_model,
                                }
                                issue["verification"]["verification_rationale"] = read_review(v_output_file)
                                if status == "INVALIDATED":
                                    issue["status"] = "invalidated_by_verifier"
                                    issue.setdefault("adjudication", {})["status"] = "invalidated_by_verifier"
                                break
                    else:
                        print(
                            f"[Verification] {vp['issue_id']}: verifier failed (exit {v_rc})",
                            file=sys.stderr,
                        )
                # Re-save ledger after verification updates
                save_ledger(ledger_file, ledger)

    if verdict_ledger is not ledger:
        _sync_verification_state(verdict_ledger, ledger)

    # Early exit signal for host agent
    early_exit, early_exit_reason = should_exit_early(
        verdict_ledger, args.threshold, active_panel_size
    )

    # Check parse status — detect all-unstructured reviews
    parse_statuses = []
    for idx, (_provider, _model) in enumerate(panel, 1):
        review_file = str(Path(tmpdir) / f"qr-{quorum_id}-r{idx}-review.md")
        parsed = parse_structured_review(review_file)
        parse_statuses.append(parsed["structured"])
    all_unstructured = not any(parse_statuses)
    unstructured_count = sum(1 for s in parse_statuses if not s)

    # Derive verdict from surviving blocking issues
    derived_verdict, surviving_issues, dropped_issues = derive_verdict(
        verdict_ledger, args.threshold, active_panel_size
    )
    issue_consensus = format_issue_consensus(
        verdict_ledger, args.threshold, active_panel_size
    )

    # Write deliberation file for next round
    delib_out = args.deliberation_file or str(
        Path(tmpdir) / f"qr-{quorum_id}-deliberation.md"
    )
    Path(delib_out).write_text(deliberation_text, encoding="utf-8")

    # Write tally as JSON
    tally_data = {
        "round": round_num,
        "threshold": args.threshold,
        "original_panel_size": original_panel_size,
        "active_panel_size": active_panel_size,
        "on_failure": args.on_failure,
        "mode": args.mode,
        "advisory_threshold_met": tally["threshold_met"],
        "derived_verdict": derived_verdict,
        "surviving_blockers": len(surviving_issues),
        "dropped_blockers": len(dropped_issues),
        "approved_count": len(tally["approved"]),
        "revise_count": len(tally["revise"]),
        "failed_count": len(tally["failed"]),
        "total": tally["total"],
        "all_unstructured": all_unstructured,
        "unstructured_count": unstructured_count,
        "reviewers": [
            {
                "label": v[0],
                "verdict": v[1],
                "model": v[2],
                "effort": v[3],
            }
            for v in verdicts
        ],
        "reviewer_map": {
            label: info for label, info in reviewer_map.items()
        },
        "exit_codes": results,
        "early_exit": early_exit,
        "early_exit_reason": early_exit_reason,
        "merge_log_path": merge_result["log_path"],
        "merged_count": len(merge_result["merged"]),
        "merge_candidate_count": len(merge_result["candidates"]),
        "verifier": verifier_spec,
    }
    tally_file = args.tally_file or str(Path(tmpdir) / f"qr-{quorum_id}-tally.json")
    Path(tally_file).write_text(json.dumps(tally_data, indent=2), encoding="utf-8")

    # Print summary to stdout for host agent consumption
    print(f"\n## Quorum Review — Round {round_num} Tally\n")
    print(tally["summary"])
    if unstructured_count > 0:
        print(
            f"\nWARNING: {unstructured_count}/{len(panel)} reviewer(s) produced "
            "unstructured output (parse_status: unstructured)"
        )
    print(f"\n{issue_consensus}")
    if early_exit:
        print(f"\nEARLY EXIT SIGNAL: {early_exit_reason}")
    print(f"\nDeliberation context written to: {delib_out}")
    print(f"Tally written to: {tally_file}")
    print(f"Issue ledger written to: {ledger_file}")

    # Exit codes: 0=APPROVED, 2=REVISE, 3=INDETERMINATE
    if all_unstructured:
        print("\nINDETERMINATE: all reviews were unstructured")
        sys.exit(EXIT_INDETERMINATE)
    elif derived_verdict == "APPROVED":
        print("\nDERIVED CONSENSUS: APPROVED")
        sys.exit(EXIT_APPROVED)
    else:
        print(f"\nDERIVED CONSENSUS: REVISE ({len(surviving_issues)} blocker(s) survive)")
        sys.exit(EXIT_REVISE)
