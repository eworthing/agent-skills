#!/usr/bin/env python3
"""Selftest for the site-pass roster binding in scripts/candidate_fingerprint.py (SITE-PASS plan
W1). Run directly; exit 0 = pass. Guards: a review without a roster produces the pre-epoch payload
(no roster key, so historical fingerprints are unchanged); a roster digest changes the fingerprint;
a narrowed roster (different digest) never matches the full one.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import candidate_fingerprint as CF


def _review(roster: dict | None) -> dict:
    d: dict = {"lens": "Apple", "source_roots": ["Kit/Sources"]}
    if roster is not None:
        d["site_pass_roster"] = roster
    return {"discovery": d, "scorecard": {}, "findings": []}


def test_absent_roster_keeps_payload_shape() -> None:
    payload = CF._architecture_payload(_review(None))
    assert "site_pass_roster_digest" not in payload, payload
    payload = CF._architecture_payload(_review({"paths": [], "digest": ""}))
    assert "site_pass_roster_digest" not in payload, "empty digest must not bind"


def test_roster_digest_binds() -> None:
    full = CF.candidate_fingerprint(_review({"paths": ["a", "b"], "digest": "d-full"}))
    narrowed = CF.candidate_fingerprint(_review({"paths": ["a"], "digest": "d-narrow"}))
    none = CF.candidate_fingerprint(_review(None))
    assert full != narrowed and full != none and narrowed != none
    assert CF.candidate_fingerprint(_review({"paths": ["a", "b"], "digest": "d-full"})) == full


if __name__ == "__main__":
    for _name, _fn in sorted(globals().items()):
        if _name.startswith("test_") and callable(_fn):
            _fn()
            print(f"PASS {_name}")
    print("candidate_fingerprint selftest: OK")
