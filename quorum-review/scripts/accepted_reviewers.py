"""
accepted_reviewers.py — Single source of truth for the providers
quorum-review accepts as reviewers.

The plan's invariant #2 requires this skill to accept exactly
{claude, gemini, codex, copilot, agy} and never expose opencode through any
provider-enumeration path (argparse, --list-models, --self-check, --help,
error messages, internal dispatch). All those paths read from
``accepted_reviewers()`` so the allow-list is centralized.

Phase B introduces this module. Phase C migrates the canonical
definition into ``quorum/cli.py`` and leaves this file as a one-line
re-export shim so existing imports continue to work.
"""

ACCEPTED_REVIEWERS: tuple[str, ...] = ("claude", "gemini", "codex", "copilot", "agy")


def accepted_reviewers() -> tuple[str, ...]:
    """Return the tuple of accepted reviewer provider names."""
    return ACCEPTED_REVIEWERS
