#!/usr/bin/env python3
"""Score harness outputs against the fixture answer key.

Usage:
  python3 score.py baseline    # verdict + finding counts + format/parse per run
  python3 score.py microtest   # per-battery control-vs-treat signal counts

Reads runs/<mode>/*-review.md produced by run_reviews.py. Uses the skill's own
parse_structured_review so 'does it parse' is part of the score. Manual reads of
flagged matches are still required for the judgment-subtle batteries (f2/f3) —
this only prescreens.

Scoring semantics:
- A missing/empty run file is transport failure, not reviewer behavior: it is
  EXCLUDED from its arm's denominator and labeled ``NO OUTPUT (excluded)``. An
  arm with <2 valid runs reports ``INSUFFICIENT DATA`` instead of a count.
- ``parse=ok`` iff BOTH ``### Blocking Issues`` and ``### Non-Blocking Issues``
  headings are present (case-insensitive) AND a valid verdict parsed; the
  finding count may then legitimately be 0 (``parse=ok findings=0``). Anything
  else is ``parse=MALFORMED``.
"""

import functools
import pathlib
import re
import statistics
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
from _common.session import (  # noqa: E402
    _extract_section,
    _parse_verdict,
    parse_structured_review,
)

OBS = re.compile(r"observab|metric|logging|\blog\b|monitor|telemetry|instrument|alert", re.I)
MONEY = re.compile(r"monetar|floating[- ]?point|rounding|decimal|currency|\bmoney\b|cents?\b", re.I)
UNDEF = re.compile(r"enqueue_digest_job|DigestScheduler", re.I)
USPEC = re.compile(r"error handling|retr(y|ies)|backoff", re.I)
BADCRIT = re.compile(
    r"contradict|bypass|self[- ]?serv|in tension|criterion 3|third criterion|conflict|inconsistent",
    re.I,
)
EH_FLAG = re.compile(
    r"error handling|retr(y|ies)|transient|idempoten|no explicit|unverified|hedge|defer", re.I
)

_HEADINGS = (
    re.compile(r"^###\s+Blocking Issues\s*$", re.I | re.M),
    re.compile(r"^###\s+Non-Blocking Issues\s*$", re.I | re.M),
)


@functools.cache
def _read_review_file(path_str):
    p = pathlib.Path(path_str)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def review(mode, label):
    p = HERE / "runs" / mode / f"{label}-review.md"
    return _read_review_file(str(p))


@functools.cache
def findings(txt):
    return parse_structured_review(txt) or []


def ftext(fs):
    return " ".join(f.get("description", "") + " " + f.get("recommendation", "") for f in fs)


def parse_ok(txt):
    """True iff both findings headings are present AND a verdict parsed."""
    return all(rx.search(txt) for rx in _HEADINGS) and _parse_verdict(None, text=txt) is not None


def findings_sections(txt):
    """The two findings sections only — scopes prescreen regexes so prose in
    Reasoning/preamble (quoting the planted text back) can't count as a hit."""
    return (
        _extract_section(txt, "Blocking Issues")
        + "\n"
        + _extract_section(txt, "Non-Blocking Issues")
    )


def score_baseline():
    for label in ("std-sonnet", "std-codex", "domain", "adversarial"):
        txt = review("baseline", label)
        if not txt:
            print(f"{label:12s}: NO OUTPUT (excluded)")
            continue
        fs = findings(txt)
        nb = sum(1 for x in fs if x.get("severity") == "blocking")
        verdict = _parse_verdict(None, text=txt) or "(no VERDICT line)"
        obs = "obs✓" if OBS.search(ftext(fs)) else "obs✗"
        parse = f"ok findings={len(fs)}" if parse_ok(txt) else "MALFORMED"
        print(
            f"{label:12s}: {verdict[:30]:30s} blocking={nb} nonblk={len(fs) - nb} {obs} parse={parse}"
        )


def score_microtest(reps=5):
    def col(bat, arm, fn):
        """Apply fn over VALID runs only. Returns (values, excluded_count);
        values is None when the arm has <2 valid runs."""
        txts = [review("microtest", f"{bat}-{arm}-{r}") for r in range(1, reps + 1)]
        valid = [t for t in txts if t]
        excluded = len(txts) - len(valid)
        if len(valid) < 2:
            return None, excluded
        return [fn(t) for t in valid], excluded

    def note(excluded):
        return f" ({excluded} run(s) NO OUTPUT, excluded)" if excluded else ""

    def insufficient(arm, excluded):
        print(f"  {arm:7s}: INSUFFICIENT DATA (<2 valid runs){note(excluded)}")

    print("L-OBS — finding flags observability:")
    for arm in ("control", "treat"):
        hits, ex = col("obs", arm, lambda t: bool(OBS.search(ftext(findings(t)))))
        if hits is None:
            insufficient(arm, ex)
            continue
        print(f"  {arm:7s}: {sum(hits)}/{len(hits)} {hits}{note(ex)}")

    print("F4 — finding-count variance + money-anchor leak:")
    for arm in ("control", "treat"):
        vals, ex = col(
            "ex", arm, lambda t: (len(findings(t)), bool(MONEY.search(ftext(findings(t)))))
        )
        if vals is None:
            insufficient(arm, ex)
            continue
        cs = [v[0] for v in vals]
        an = [v[1] for v in vals]
        print(
            f"  {arm:7s}: counts={cs} sd={statistics.pstdev(cs):.2f} "
            f"anchor-leak={sum(an)}/{len(an)}{note(ex)}"
        )

    print("L-SEV — seam classification (B/N/-):")

    def cls(t, rx):
        fs = findings(t)
        b = any(
            rx.search(f.get("description", "") + f.get("recommendation", ""))
            for f in fs
            if f.get("severity") == "blocking"
        )
        n = any(
            rx.search(f.get("description", "") + f.get("recommendation", ""))
            for f in fs
            if f.get("severity") != "blocking"
        )
        return "B" if b else ("N" if n else "-")

    for arm in ("control", "treat"):
        vals, ex = col("sev", arm, lambda t: (cls(t, UNDEF), cls(t, USPEC)))
        if vals is None:
            insufficient(arm, ex)
            continue
        u = [v[0] for v in vals]
        s = [v[1] for v in vals]
        print(f"  {arm:7s}: UNDEF {u} | UNSPEC {s}{note(ex)}")

    print("F2 — Pass B challenges planted bad criterion (PRESCREEN — read matches):")
    for arm in ("control", "treat"):
        h, ex = col("f2", arm, lambda t: bool(BADCRIT.search(findings_sections(t))))
        if h is None:
            insufficient(arm, ex)
            continue
        print(f"  {arm:7s}: {sum(h)}/{len(h)} {h}{note(ex)}")

    print("F3 — adversarial flags deferred error handling (PRESCREEN — read matches):")
    for arm in ("control", "treat"):
        h, ex = col(
            "f3",
            arm,
            lambda t: any(
                EH_FLAG.search(f.get("description", "") + f.get("recommendation", ""))
                for f in findings(t)
            ),
        )
        if h is None:
            insufficient(arm, ex)
            continue
        print(f"  {arm:7s}: {sum(h)}/{len(h)} {h}{note(ex)}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    if mode == "baseline":
        score_baseline()
    elif mode == "microtest":
        score_microtest(int(sys.argv[2]) if len(sys.argv) > 2 else 5)
    else:
        sys.exit(f"unknown mode: {mode!r}")
