"""quorum.prompts — review contracts, role packs, and per-round prompt writers.

Sections (in order):
    # === review contracts ===              ``REVIEW_CONTRACT_PLAN``,
                                            ``REVIEW_CONTRACT_SPEC``,
                                            ``REVIEW_CONTRACT_V2``,
                                            ``REVIEW_CONTRACT_CODE``,
                                            ``CROSS_CRITIQUE_INSTRUCTIONS``,
                                            ``VERIFICATION_CONTRACT``
    # === role packs / mode helpers ===     ``MODE_ROLE_PACKS``,
                                            ``_normalize_mode``,
                                            ``_review_contract_for_mode``,
                                            ``_artifact_heading_for_mode``,
                                            ``_artifact_lower_for_mode``,
                                            ``_role_for_mode``
    # === REVIEW.md rubric loader ===       ``load_review_md``
    # === plan numbering / anchor format == ``_number_plan``,
                                            ``_format_anchor_for_prompt``
    # === prompt writers ===                ``write_initial_prompt``,
                                            ``write_deliberation_prompt``,
                                            ``write_cross_critique_prompt``
    # === ledger summary ===                ``format_ledger_summary``

Depends on ``quorum.ledger`` for the issue accessors used by
``format_ledger_summary``. No dep on parsing/merge/verification/orchestrator,
so this module is safely importable from verification (for
``VERIFICATION_CONTRACT`` and ``_format_anchor_for_prompt``) and from
orchestrator. When adding a function, slot it under the matching section
header rather than appending to the bottom (see CONTRIBUTING.md).
"""

from pathlib import Path

from quorum.ledger import (
    _issue_dispute_count,
    _issue_status,
    _issue_support_count,
)

# ---------------------------------------------------------------------------
# === review contracts ===
# ---------------------------------------------------------------------------

REVIEW_CONTRACT_PLAN = (
    "## Review Contract\n\n"
    "You are reviewing a plan or spec as part of a multi-reviewer quorum panel.\n\n"
    "Structure your review using EXACTLY these sections:\n\n"
    "### Reasoning\n"
    "Write your complete analysis of the plan here. Consider architecture,\n"
    "security, testing, performance, and any other relevant areas. This\n"
    "section MUST come before your issue lists.\n\n"
    "### Blocking Issues\n"
    "Issues that MUST be resolved before execution. Use [B1], [B2], etc.\n"
    "Optionally include per-issue confidence: (HIGH), (MEDIUM), or (LOW).\n"
    "For each issue, include a Section: line referencing the plan section name\n"
    "and line numbers from the numbered plan (e.g., Section: Step 3 (lines 42-55)).\n"
    "- [B1] (HIGH) Description of blocking issue...\n"
    "  Section: <plan section> (lines <N-M>)\n"
    "  Recommendation: Concrete fix or mitigation\n"
    "- [B2] (MEDIUM) Description of blocking issue...\n"
    '(Write "None" if no blocking issues.)\n\n'
    "### Non-Blocking Issues\n"
    "Suggestions and improvements. Use [N1], [N2], etc.\n"
    "- [N1] Description...\n"
    "  Section: <plan section> (lines <N-M>)\n"
    "  Recommendation: Suggested improvement\n"
    '(Write "None" if no non-blocking issues.)\n\n'
    "### Confidence\n"
    "State your confidence in this review: HIGH, MEDIUM, or LOW\n\n"
    "### Scope\n"
    'Which areas of the plan does your review cover? (e.g., "architecture",\n'
    '"security", "testing", "API design", "performance")\n\n'
    "Your review MUST end with a verdict on the LAST non-empty line:\n"
    "- `VERDICT: APPROVED` if the plan is ready to execute as-is\n"
    "- `VERDICT: REVISE` if changes are needed before execution\n\n"
    "The verdict line must be EXACTLY one of these two strings, nothing else."
)

REVIEW_CONTRACT_SPEC = REVIEW_CONTRACT_PLAN
REVIEW_CONTRACT_V2 = REVIEW_CONTRACT_PLAN

CROSS_CRITIQUE_INSTRUCTIONS = (
    "## Cross-Critique Instructions\n\n"
    "Below are anonymous reviews from the prior round and the current issue ledger.\n\n"
    "### Part 1: Respond to every open issue\n\n"
    "For EACH open issue in the Current Issue Ledger section below, write exactly\n"
    "one response. Every issue needs your position — if you skip an issue, the\n"
    "orchestrator records no data from you on it, which weakens the consensus.\n\n"
    "- `[AGREE BLK-001]` — you confirm this issue is valid\n"
    "- `[DISAGREE BLK-001] reason` — you dispute this issue (include your reasoning)\n"
    "- `[REFINE BLK-001] revised description` — the concern is valid but you want to\n"
    "  adjust its scope or description (counts as support, like AGREE)\n\n"
    "You may also raise entirely new issues discovered in this round:\n"
    "- `[B-NEW] description` — new blocking issue\n"
    "- `[N-NEW] description` — new non-blocking issue\n\n"
    "Put all cross-critique responses together BEFORE your review sections.\n\n"
    "### Part 2: Updated structured review\n\n"
    "After your cross-critique responses, provide your full updated review using\n"
    "the standard sections (### Reasoning, ### Blocking Issues, ### Non-Blocking\n"
    "Issues, ### Confidence, ### Scope) and end with your VERDICT line.\n\n"
    "### Example round 2+ response\n\n"
    "```\n"
    "[AGREE BLK-001]\n"
    "[DISAGREE BLK-002] The plan already handles this via the retry middleware\n"
    "[REFINE NB-001] Should also cover WebSocket connections, not just HTTP\n"
    "[B-NEW] No rate limiting on the public API endpoints\n\n"
    "### Reasoning\n"
    "After reviewing the other panelists' feedback...\n\n"
    "### Blocking Issues\n"
    "- [B1] (HIGH) BLK-001 remains unaddressed — auth is still missing\n"
    "  Section: Auth middleware (lines 12-18)\n"
    "  Recommendation: Add role-based access control before deployment\n"
    "- [B2] (MEDIUM) New: No rate limiting on public API\n"
    "  Section: API gateway (lines 34-40)\n"
    "  Recommendation: Add token-bucket rate limiter\n\n"
    "### Non-Blocking Issues\n"
    "None\n\n"
    "### Confidence\n"
    "HIGH\n\n"
    "### Scope\n"
    "security, API design\n\n"
    "VERDICT: REVISE\n"
    "```"
)

REVIEW_CONTRACT_CODE = (
    "## Review Contract\n\n"
    "You are reviewing a code change as part of a multi-reviewer quorum panel.\n\n"
    "Structure your review using EXACTLY these sections:\n\n"
    "### Reasoning\n"
    "Write your complete analysis of the change here. Consider correctness,\n"
    "security, performance, maintainability, and operational risk. This section\n"
    "MUST come before your issue lists.\n\n"
    "### Blocking Issues\n"
    "Issues that MUST be resolved before execution. Use [B1], [B2], etc.\n"
    "For each issue, include an Anchor line naming a file/path and either a line\n"
    "range or a diff hunk. Examples:\n"
    "- [B1] (HIGH) Missing auth check on admin handler\n"
    "  Anchor: src/auth/admin.ts (lines 45-52)\n"
    "  Recommendation: Add the missing authorization guard\n"
    "- [B2] (MEDIUM) Diff hunk still allows unsafe fallback\n"
    "  Anchor: diff hunk @@ -12,7 +12,9 @@\n"
    "  Recommendation: Remove the fallback branch\n"
    '(Write "None" if no blocking issues.)\n\n'
    "### Non-Blocking Issues\n"
    "Suggestions and improvements. Use [N1], [N2], etc.\n"
    "Include an Anchor line when the note refers to a specific file or hunk.\n"
    '(Write "None" if no non-blocking issues.)\n\n'
    "### Confidence\n"
    "State your confidence in this review: HIGH, MEDIUM, or LOW\n\n"
    "### Scope\n"
    'Which areas of the change does your review cover? (e.g., "correctness",\n'
    '"security", "maintainability", "performance", "operability")\n\n'
    "Your review MUST end with a verdict on the LAST non-empty line:\n"
    "- `VERDICT: APPROVED` if the change is ready to land as-is\n"
    "- `VERDICT: REVISE` if changes are needed before landing\n\n"
    "The verdict line must be EXACTLY one of these two strings, nothing else."
)

VERIFICATION_CONTRACT = (
    "## Verification Contract\n\n"
    "You are an independent verifier outside the panel.\n"
    "Use only the blocker ID, anchor data, the current artifact/context, and the blocker\n"
    "summary to decide whether the concern still holds.\n\n"
    "Respond with EXACTLY one of these on the first non-empty line:\n"
    "- `VERIFIED <BLOCKER_ID>` — the blocker is still valid\n"
    "- `INVALIDATED <BLOCKER_ID>` — the blocker is no longer valid\n\n"
    "Then add one concise rationale grounded in the artifact text."
)


# ---------------------------------------------------------------------------
# === role packs / mode helpers ===
# ---------------------------------------------------------------------------

MODE_ROLE_PACKS = {
    "plan": [
        "Skeptic",
        "Constraint Guardian",
        "User Advocate",
        "Integrator-minded reviewer",
    ],
    "spec": [
        "Skeptic",
        "Constraint Guardian",
        "User Advocate",
        "Integrator-minded reviewer",
    ],
    "code": [
        "Correctness reviewer",
        "Security reviewer",
        "Maintainability reviewer",
        "Performance/operability reviewer",
    ],
}


def _normalize_mode(mode):
    return "code" if mode == "code" else "plan"


def _review_contract_for_mode(mode):
    return REVIEW_CONTRACT_CODE if _normalize_mode(mode) == "code" else REVIEW_CONTRACT_PLAN


def _artifact_heading_for_mode(mode):
    return "Code Change" if _normalize_mode(mode) == "code" else "Plan"


def _artifact_lower_for_mode(mode):
    return _artifact_heading_for_mode(mode).lower()


def _role_for_mode(mode, reviewer_index):
    pack = MODE_ROLE_PACKS[_normalize_mode(mode)]
    return pack[(reviewer_index - 1) % len(pack)]


# ---------------------------------------------------------------------------
# === REVIEW.md rubric loader ===
# ---------------------------------------------------------------------------


def load_review_md(directory=None):
    """Load REVIEW.md from the given directory (or cwd) if it exists.

    Returns the file contents as a string, or empty string if not found.
    """
    review_path = Path(directory or ".").resolve() / "REVIEW.md"
    if review_path.exists():
        try:
            return review_path.read_text(encoding="utf-8").strip()
        except OSError:
            return ""
    return ""


# ---------------------------------------------------------------------------
# === plan numbering / anchor format ===
# ---------------------------------------------------------------------------


def _number_plan(plan_text):
    """Add line numbers to plan text for reviewer citation."""
    lines = plan_text.split("\n")
    width = len(str(len(lines)))
    return "\n".join(f"{i + 1:>{width}}\t{line}" for i, line in enumerate(lines))


def _format_anchor_for_prompt(anchor):
    anchor = anchor if isinstance(anchor, dict) else {}
    if not anchor:
        return "None"
    lines = []
    for key in (
        "artifact_kind",
        "artifact_path",
        "anchor_kind",
        "anchor_start",
        "anchor_end",
        "anchor_hash",
        "section",
        "path",
        "kind",
        "line_start",
        "line_end",
        "raw",
    ):
        value = anchor.get(key)
        if value not in (None, "", []):
            lines.append(f"- {key}: {value}")
    if not lines:
        return "None"
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# === prompt writers ===
# ---------------------------------------------------------------------------


def write_initial_prompt(
    prompt_file,
    reviewer_index,
    total_reviewers,
    review_contract,
    plan_text,
    rubric_text="",
    mode="plan",
    role_label=None,
    artifact_heading="Plan",
):
    """Write the initial review prompt for round 1."""
    rubric_section = ""
    if rubric_text:
        rubric_section = f"\n\n## Project Review Guidelines\n\n{rubric_text}\n"
    artifact_lower = artifact_heading.lower()
    role_line = f"Your private role for this round is: {role_label}.\n" if role_label else ""

    content = (
        f"{review_contract}{rubric_section}\n\n"
        f"## Panel Context\n\n"
        f"You are reviewer {reviewer_index} of {total_reviewers} in a quorum review panel.\n"
        f"{role_line}"
        f"Other reviewers are also evaluating this {artifact_lower} independently. In subsequent\n"
        f"rounds you will see their feedback and can respond to it. For now, provide\n"
        f"your independent assessment.\n\n"
        f"## {artifact_heading}\n\n"
        f"{_number_plan(plan_text)}\n"
    )

    Path(prompt_file).write_text(content, encoding="utf-8")


def write_deliberation_prompt(
    prompt_file,
    reviewer_index,
    total_reviewers,
    round_num,
    review_contract,
    deliberation_text,
    changes_summary,
    plan_text,
    mode="plan",
    role_label=None,
    artifact_heading="Plan",
):
    """Write the deliberation prompt for a specific reviewer in rounds 2+."""
    artifact_lower = artifact_heading.lower()
    role_line = f"Your private role for this round is: {role_label}.\n" if role_label else ""
    content = (
        f"{review_contract}\n\n"
        f"## Panel Context\n\n"
        f"You are reviewer {reviewer_index} of {total_reviewers} in a quorum review panel.\n"
        f"{role_line}"
        f"This is round {round_num}. Below are ALL reviews from the previous round,\n"
        f"including your own. Consider the other reviewers' points carefully.\n"
        f"You may agree, disagree, or refine their feedback. The host has revised\n"
        f"the {artifact_lower} based on the combined feedback.\n\n"
        f"## Reviews from Previous Round\n\n"
        f"{deliberation_text}\n\n"
        f"## Changes Since Last Round (by HOST)\n\n"
        f"{changes_summary}\n\n"
        f"## Updated {artifact_heading}\n\n"
        f"{_number_plan(plan_text)}\n"
    )

    Path(prompt_file).write_text(content, encoding="utf-8")


def write_cross_critique_prompt(
    prompt_file,
    reviewer_index,
    total_reviewers,
    round_num,
    review_contract,
    cross_critique_instructions,
    deliberation_or_compressed,
    ledger_summary,
    changes_summary,
    plan_text,
    mode="plan",
    role_label=None,
    artifact_heading="Plan",
):
    """Write round 2+ prompt with cross-critique instructions and issue ledger."""
    role_line = f"Your private role for this round is: {role_label}.\n" if role_label else ""
    content = (
        f"{review_contract}\n\n"
        f"{cross_critique_instructions}\n\n"
        f"## Panel Context\n\n"
        f"You are reviewer {reviewer_index} of {total_reviewers} in a quorum review panel.\n"
        f"{role_line}"
        f"This is round {round_num}. All reviewer identities are anonymous.\n\n"
        f"## Reviews from Previous Round\n\n"
        f"{deliberation_or_compressed}\n\n"
        f"## Current Issue Ledger\n\n"
        f"{ledger_summary}\n\n"
        f"## Changes Since Last Round (by HOST)\n\n"
        f"{changes_summary}\n\n"
        f"## Updated {artifact_heading}\n\n"
        f"{_number_plan(plan_text)}\n"
    )

    Path(prompt_file).write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# === ledger summary ===
# ---------------------------------------------------------------------------


def format_ledger_summary(ledger, blind_mode=False):
    """Format the issue ledger as a markdown summary for reviewer prompts.

    When blind_mode=True, omits support/dispute counts to prevent conformity
    anchoring in later rounds.
    """
    open_issues = [i for i in ledger["issues"] if _issue_status(i) == "open"]
    if not open_issues:
        return "No open issues."

    lines = []
    for issue in open_issues:
        if blind_mode:
            lines.append(f"- **{issue['id']}** ({issue['severity']}): {issue['owner_summary']}")
        else:
            lines.append(
                f"- **{issue['id']}** ({issue['severity']}): {issue['owner_summary']} "
                f"[support: {_issue_support_count(issue)}, disputes: {_issue_dispute_count(issue)}]"
            )
    return "\n".join(lines)
