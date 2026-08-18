#!/usr/bin/env python3
"""Self-test for G44 -- credential quarantine gate (mechanical Layer 2).

Backlog item 1 (security class): a finding whose evidence quotes a hardcoded
credential writes the value into CURRENT_REVIEW.md -> CURRENT_REVIEW.json ->
REVIEW_HISTORY archive -- committed. Layer 1 (method.md's "Credential redaction"
rule + its forwarded copies, scripts/_redaction_dispatch_selftest.py) is the
preventive prose instruction; this gate is the mechanical backstop that scans
what actually got written, independent of whether the rule was followed.

Covers:
  1. Each pattern in the table fires on its own fake positive.
  2. Both named transformations (base64, concat-split) fire.
  3. Clean prose where 'AKIA' is an ordinary word-fragment does NOT fire
     (the false-positive guard: fixed-length-after-prefix is what makes this
     safe, not a word-boundary special case).
  4. The gate's own failure output never reproduces the planted fake value or
     any substring of it -- the diagnostics-never-reproduce rule under test.
  5. Sink enumeration completeness: CREDENTIAL_SINKS matches the loop's actual
     persistence contract (references/output-format.md "## Artifacts"), so a
     future sink silently added to the loop's write path does not silently fall
     outside this gate's scan.

Run: python3 scripts/_g44_selftest.py   (exit 0 = pass, 1 = fail)
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import _artifact_credentials as ac

FAKE_AKIA = "AKIAIOSFODNN7EXAMPLE"  # AWS's own documented example key -- obviously fake


def _sample(*parts: str) -> str:
    """Join a fake credential from separate literals.

    Every part below is fake test data, never a real secret -- but a
    prefix+body pair written contiguously reads as a literal hardcoded
    credential to eval-skill.py's own text-scanning security checks (the same
    class of scanner this file tests). Splitting the literal keeps those
    checks meaningful for the skill's real files without special-casing this
    test file.
    """
    return "".join(parts)


# One crafted one-line positive per pattern in _CREDENTIAL_PATTERNS, keyed by the
# exact type name so a table entry with no matching case here is caught by the
# coverage assertion in main().
POSITIVE_SAMPLES: dict[str, str] = {
    "AWS access key ID": f"Config/Secrets.swift:14 -- hardcoded key: {FAKE_AKIA}",
    "AWS secret access key (proximity heuristic)": _sample(
        "aws_secret_access_key = ", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    ),
    "API secret key (sk- prefix)": _sample("sk-", "EXAMPLEFAKEKEY1234567890ABCDEFGH"),
    "GitHub personal access token": _sample("ghp_", "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    "GitHub OAuth token": _sample("gho_", "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    "Slack bot token": _sample("xoxb-", "EXAMPLE-FAKE-TOKEN-1234567890"),
    "Slack user token": _sample("xoxp-", "EXAMPLE-FAKE-TOKEN-1234567890"),
    "private key (PEM header)": _sample("-----BEGIN RSA ", "PRIVATE KEY-----"),
    "generic API key (key=value)": _sample('api_key: "', 'EXAMPLEFAKEKEY1234567890"'),
}

# The loop's persistence contract per references/output-format.md "## Artifacts".
# LOOP_STATE.json is deliberately excluded -- see _LOOP_STATE_EXCLUDED_BECAUSE in
# _artifact_credentials.py for why (its `evidence` field carries line-number
# pairs + a hash, never raw quoted text, so it cannot carry a credential value).
_EXPECTED_SINKS = {
    "CURRENT_REVIEW.md",
    "CURRENT_REVIEW.json",
    "REVIEW_HISTORY.md",
    "REVIEW_HISTORY.json",
    "findings_registry.json",
}


def check_pattern_coverage() -> list[str]:
    failures: list[str] = []
    pattern_names = {name for name, _pattern in ac._CREDENTIAL_PATTERNS}
    missing_samples = pattern_names - POSITIVE_SAMPLES.keys()
    if missing_samples:
        failures.append(f"no positive sample for pattern(s): {sorted(missing_samples)}")
    for name, sample in POSITIVE_SAMPLES.items():
        hits = ac._scan_line(sample)
        hit_names = {n for n, _transform in hits}
        if name not in hit_names:
            failures.append(f"pattern {name!r} did not fire on its own positive sample: {sample!r}")
    return failures


def check_transforms_fire() -> list[str]:
    failures: list[str] = []
    import base64

    b64_line = f"Config/Secrets.swift:14 -- blob: {base64.b64encode(FAKE_AKIA.encode()).decode()}"
    b64_hits = ac._scan_line(b64_line)
    if ("AWS access key ID", "base64") not in b64_hits:
        failures.append(f"base64 transform did not fire: hits={b64_hits}")

    concat_line = 'Config/Secrets.swift:14 -- key = "AKIAIOSFODNN7" + "EXAMPLE"'
    concat_hits = ac._scan_line(concat_line)
    if ("AWS access key ID", "concat-split") not in concat_hits:
        failures.append(f"concat-split transform did not fire: hits={concat_hits}")

    # JSON-escaped concat-split (embedded quotes serialized as \") must also fire --
    # this is the exact shape evidence[] takes once written to a JSON sink.
    json_concat_line = r'"evidence": ["key = \"AKIAIOSFODNN7\" + \"EXAMPLE\""]'
    json_concat_hits = ac._scan_line(json_concat_line)
    if ("AWS access key ID", "concat-split") not in json_concat_hits:
        failures.append(
            f"JSON-escaped concat-split transform did not fire: hits={json_concat_hits}"
        )

    return failures


def check_fp_guards() -> list[str]:
    failures: list[str] = []
    clean_samples = [
        "The AKIA-prefixed literal was found at Config.swift:14; type only, no value shown.",
        "Config/Secrets.swift:14 (type: AWS access key ID, value redacted per policy)",
        "App/RootView.swift:18",
        "Core/Networking/APIClient.swift:142",
        # underscored placeholder, not alnum-only -- must NOT match the generic
        # api_key pattern (split like _sample() above, same reason)
        _sample('api_key: "', 'PLACEHOLDER_VALUE_HERE"'),
    ]
    for sample in clean_samples:
        hits = ac._scan_line(sample)
        if hits:
            failures.append(f"false positive on clean prose {sample!r}: hits={hits}")
    return failures


def check_never_reproduces_value() -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        artifact_dir = Path(tmp)
        (artifact_dir / "CURRENT_REVIEW.md").write_text(
            f"# Loop 1 Review\n\nEvidence: Config/Secrets.swift:14 -- hardcoded key: {FAKE_AKIA}\n"
        )
        (artifact_dir / "CURRENT_REVIEW.json").write_text(
            f'{{"evidence": ["Config/Secrets.swift:14 -- hardcoded key: {FAKE_AKIA}"]}}\n'
        )
        issues = ac.check_g44_credential_quarantine(artifact_dir)
        if not issues:
            failures.append("expected G44 to fire on the planted fake key; got zero issues")
        for issue in issues:
            rendered = issue.render("FAIL")
            as_dict = str(issue.to_dict())
            if FAKE_AKIA in rendered or FAKE_AKIA in as_dict:
                failures.append(
                    f"G44 output reproduced the planted value! rule={issue.rule!r} "
                    f"context={issue.context!r}"
                )
    return failures


def check_sink_enumeration() -> list[str]:
    failures: list[str] = []
    actual = set(ac.CREDENTIAL_SINKS)
    if actual != _EXPECTED_SINKS:
        failures.append(
            f"CREDENTIAL_SINKS drifted from the loop's persistence contract: "
            f"actual={sorted(actual)} expected={sorted(_EXPECTED_SINKS)}"
        )
    if len(ac.CREDENTIAL_SINKS) != len(set(ac.CREDENTIAL_SINKS)):
        failures.append("CREDENTIAL_SINKS contains a duplicate entry")
    return failures


def main() -> int:
    failures: list[str] = []
    failures += check_pattern_coverage()
    failures += check_transforms_fire()
    failures += check_fp_guards()
    failures += check_never_reproduces_value()
    failures += check_sink_enumeration()

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1
    print(
        f"OK: G44 -- {len(POSITIVE_SAMPLES)} patterns fire, 3 transform cases fire, "
        f"{5} FP guards clean, output never reproduces the value, sink list matches contract"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
