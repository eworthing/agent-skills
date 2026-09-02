"""_artifact_md_flag.py — G51: the CURRENT_REVIEW.md System Flag mirrors CURRENT_REVIEW.json.state.

Found live (2026-09-02, opencode run 8747656f on BenchHype): main promoted the
HALT_SUCCESS_candidate to HALT_SUCCESS in the JSON, appended the challenge and
handoff sections to the Markdown, and left line 11 reading
`[STATE: HALT_SUCCESS_candidate]`. Nothing read the Markdown at validation time,
so strict mode passed. This gate reads it. Epoch-scoped to the prose commit that
made the rewrite an obligation (REQUIREMENT_EPOCHS['G51_MD_STATE_PARITY'], epoch
``md_state_parity``): artifacts written before it stay green.

Only the first `[STATE: ...]` line counts — output-format-markdown.md places the
System Flag section near the top, and later prose (a handoff, a quoted template)
may legitimately repeat the token.
"""

from __future__ import annotations

import re
from pathlib import Path

import _ruleset_epoch
from _artifact_core import Issue

_FLAG_RE = re.compile(r"^\[STATE:\s*([A-Za-z_]+)\]\s*$", re.MULTILINE)


def check_g51_md_state_parity(artifact_dir: Path, current_review: dict) -> list[Issue]:
    """G51: first `[STATE: <state>]` line in CURRENT_REVIEW.md equals CURRENT_REVIEW.json.state.

    Silent (no Issue) when the epoch does not apply, when `state` is null (G36 owns
    presence), or when CURRENT_REVIEW.md is absent (the required-artifact check owns
    that). A missing flag line is an Issue: the Markdown spec requires the section.
    """
    if not _ruleset_epoch.applies("G51_MD_STATE_PARITY", current_review):
        return []
    state = current_review.get("state")
    if state is None:
        return []
    md_path = Path(artifact_dir) / "CURRENT_REVIEW.md"
    if not md_path.is_file():
        return []
    try:
        text = md_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [Issue("G51", f"CURRENT_REVIEW.md unreadable: {exc}")]
    match = _FLAG_RE.search(text)
    if match is None:
        return [
            Issue(
                "G51",
                "CURRENT_REVIEW.md has no `[STATE: <state>]` System Flag line "
                "(output-format-markdown.md § System Flag)",
            )
        ]
    md_state = match.group(1)
    if md_state != state:
        return [
            Issue(
                "G51",
                f"CURRENT_REVIEW.md System Flag reads {md_state!r} but "
                f"CURRENT_REVIEW.json.state is {state!r}; the Markdown is rewritten on "
                "every state change, including main's candidate -> HALT_SUCCESS promotion "
                "(halt-handoff.md § Promotion obligations, step 1)",
            )
        ]
    return []
