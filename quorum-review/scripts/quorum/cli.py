"""quorum.cli — argument parsing, reviewer spec parsing, verifier resolution.

Hosts the global quorum policy constants (thresholds, panel-size minimum,
max-round cap, valid provider names, verifier candidate fallback list) and
the helpers that turn raw CLI strings into validated reviewer/verifier
tuples. No dependencies on other ``quorum.*`` modules — this module is a
leaf so that ``orchestrator`` and the shim can both pull from it without
risking a cycle.
"""

import argparse
import sys


# ---------------------------------------------------------------------------
# Quorum thresholds
# ---------------------------------------------------------------------------

THRESHOLDS = {
    "unanimous": lambda approved, total: approved == total,
    "super": lambda approved, total: approved >= total - 1,
    "majority": lambda approved, total: approved > total / 2,
}

MIN_QUORUM_SIZE = 3
MAX_ROUNDS_LIMIT = 5


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

VERIFIER_CANDIDATE_SPECS = [
    ("copilot", "gpt-5.4"),
    ("claude", "opus"),
    ("gemini", "pro"),
    ("codex", "o3"),
    ("claude", "sonnet"),
    ("claude", "haiku"),
    ("gemini", "flash"),
    ("gemini", "flash-lite"),
    ("gemini", "auto"),
    ("codex", "o4-mini"),
    ("copilot", None),
    ("claude", None),
    ("gemini", None),
    ("codex", None),
]


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

    if len(panel) < MIN_QUORUM_SIZE:
        print(
            f"Error: quorum requires at least {MIN_QUORUM_SIZE} reviewers, "
            f"got {len(panel)}. "
            "Add more reviewers to meet the minimum panel size.",
            file=sys.stderr,
        )
        sys.exit(1)

    return panel


def resolve_verifier(panel, verifier_spec=None):
    """Resolve an external verifier outside the active panel.

    If verifier_spec is provided, it must be a provider:model pair and must not
    match any active panel member exactly. Otherwise a deterministic external
    verifier is auto-selected from VERIFIER_CANDIDATE_SPECS.
    """
    active = {tuple(member) for member in panel}

    if verifier_spec:
        if ":" not in verifier_spec:
            print("Error: --verifier must be specified as provider:model", file=sys.stderr)
            sys.exit(1)
        provider, model = parse_reviewer_spec(verifier_spec)
        if provider not in VALID_PROVIDERS:
            print(
                f"Error: unknown verifier provider '{provider}'. "
                f"Valid: {', '.join(sorted(VALID_PROVIDERS))}",
                file=sys.stderr,
            )
            sys.exit(1)
        if not model:
            print("Error: --verifier must be specified as provider:model", file=sys.stderr)
            sys.exit(1)
        verifier = (provider, model)
        if verifier in active:
            print(
                f"Error: verifier '{provider}:{model}' is part of the active panel. "
                "Choose a verifier outside the panel.",
                file=sys.stderr,
            )
            sys.exit(1)
        return verifier

    for verifier in VERIFIER_CANDIDATE_SPECS:
        if verifier not in active:
            return verifier

    active_summary = ", ".join(f"{provider}:{model or 'default'}" for provider, model in panel)
    print(
        "Error: unable to auto-select an external verifier outside the active panel. "
        f"Active panel: {active_summary}. "
        "Pass --verifier provider:model to choose one explicitly.",
        file=sys.stderr,
    )
    sys.exit(1)


def _resolve_verifier_spec(panel, explicit_verifier=None):
    """Backward-compatible wrapper around resolve_verifier()."""
    return resolve_verifier(panel, explicit_verifier)


def parse_args():
    p = argparse.ArgumentParser(description="Quorum review orchestrator (v3)")
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
        default="super",
        choices=list(THRESHOLDS.keys()),
        help="Consensus threshold (default: super)",
    )
    p.add_argument(
        "--effort",
        default=None,
        choices=["low", "medium", "high", "xhigh"],
        help="Effort level for all reviewers",
    )
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
    p.add_argument(
        "--ledger-file",
        default=None,
        help="Path to read/write the issue ledger JSON",
    )
    p.add_argument(
        "--on-failure",
        default="shrink-quorum",
        choices=["fail-closed", "fail-open", "shrink-quorum"],
        help="How to handle reviewer failures (default: shrink-quorum)",
    )
    p.add_argument(
        "--max-rounds",
        type=int,
        default=3,
        help="Max deliberation rounds (default: 3, max: 5)",
    )
    p.add_argument(
        "--skip-verification",
        action="store_true",
        help="Skip the verification stage for surviving blockers",
    )
    p.add_argument(
        "--mode",
        default="plan",
        choices=["plan", "spec", "code"],
        help="Review mode (default: plan; plan/spec share the same tribunal path)",
    )
    p.add_argument(
        "--verifier",
        default=None,
        help="Independent verifier provider:model (auto-selects outside panel when omitted)",
    )
    args = p.parse_args()
    if args.max_rounds > MAX_ROUNDS_LIMIT:
        p.error(f"--max-rounds cannot exceed {MAX_ROUNDS_LIMIT}")
    return args
