"""Shared SHA-256 fingerprint algorithm for findings.

Single owner of the hash function. Imported by Actor/Critic emitters (when
emitting findings) AND by validate-artifact.py (when recomputing for G31
Fingerprint Integrity).

Three fingerprints per finding occurrence:
- claim_consequence_hash    Claim + Consequence (Branch A and B both gate on this)
- evidence_paths_hash       Sorted evidence[] (Branch A and B both gate on this)
- attempted_remedy_hash     Remedy (Branch A gates; Branch B does not)

See references/output-format-state-schemas.md for the canonical algorithm spec.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable

_MARKDOWN_EMPHASIS_CHARS = "*_`"
_WHITESPACE_RUN = re.compile(r"\s+")


def normalize(text: str | None) -> str:
    """Canonical normalization.

    Steps (order matters):
    1. None or non-string → empty string
    2. Lowercase
    3. Strip markdown emphasis characters: * _ `
    4. Collapse all whitespace runs (including newlines, tabs) to a single space
    5. Strip leading/trailing whitespace
    """
    if not isinstance(text, str):
        return ""
    s = text.lower()
    s = s.translate(str.maketrans("", "", _MARKDOWN_EMPHASIS_CHARS))
    s = _WHITESPACE_RUN.sub(" ", s)
    return s.strip()


def _sha256(payload: str) -> str:
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def claim_consequence_hash(
    title: str | None,
    why_it_matters: str | None,
    what_is_wrong: str | None,
    why_weakens_submission: str | None,
) -> str:
    """Hash the Claim (three fields) plus Consequence into one stable digest.

    The Evidence Chain mapping requires all three Claim fields non-empty; this
    function tolerates missing fields by normalizing to empty string, but the
    artifact validator independently rejects empty Claim fields per G2/G3.
    """
    parts = [
        normalize(title),
        normalize(why_it_matters),
        normalize(what_is_wrong),
        normalize(why_weakens_submission),
    ]
    return _sha256("\n".join(parts))


def evidence_paths_hash(evidence: Iterable[str] | None) -> str:
    """Hash the sorted list of evidence[] strings.

    Sort applied before hashing so reordering does not change the fingerprint.
    Empty list and None both hash to the same value.
    """
    items = sorted(normalize(item) for item in (evidence or []))
    return _sha256("\n".join(items))


def attempted_remedy_hash(minimal_correction_path: str | None) -> str:
    """Hash the normalized Remedy."""
    return _sha256(normalize(minimal_correction_path))


def compute_all(finding: dict) -> dict:
    """Convenience: compute the three hashes from a finding dict.

    Reads JSON field names per the Evidence Chain mapping. Returns a dict
    suitable for direct assignment into the finding's `fingerprint` object
    plus `attempted_remedy_hash`.
    """
    return {
        "fingerprint": {
            "claim_consequence_hash": claim_consequence_hash(
                finding.get("title"),
                finding.get("why_it_matters"),
                finding.get("what_is_wrong"),
                finding.get("why_weakens_submission"),
            ),
            "evidence_paths_hash": evidence_paths_hash(finding.get("evidence")),
        },
        "attempted_remedy_hash": attempted_remedy_hash(finding.get("minimal_correction_path")),
    }


if __name__ == "__main__":
    sample = {
        "title": "Navigation has two writers",
        "why_it_matters": "Multi-writer authority over UI state.",
        "what_is_wrong": "AppDelegate writes nav state; RootView also writes nav state.",
        "evidence": ["App/RootView.swift:18", "Core/NavigationStore.swift:12"],
        "why_weakens_submission": "Routing diverges; replay tests would not catch the desync.",
        "minimal_correction_path": "Move all writes to NavigationStore; AppDelegate reads via store.",
    }
    hashes = compute_all(sample)
    print(f"claim_consequence_hash:  {hashes['fingerprint']['claim_consequence_hash']}")
    print(f"evidence_paths_hash:     {hashes['fingerprint']['evidence_paths_hash']}")
    print(f"attempted_remedy_hash:   {hashes['attempted_remedy_hash']}")
