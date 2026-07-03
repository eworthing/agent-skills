#!/usr/bin/env python3
"""Score harness outputs against the fixture answer key.

Usage:
  python3 score.py baseline    # verdict + finding counts + format/parse per run
  python3 score.py microtest   # per-battery control-vs-treat signal counts

Reads runs/<mode>/*-review.md produced by run_reviews.py. Uses the skill's own
parse_structured_review so 'does it parse' is part of the score. Manual reads of
flagged matches are still required for the judgment-subtle batteries (f2/f3) —
this only prescreens.
"""
import functools, sys, re, pathlib, statistics
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
from _common.session import _parse_verdict, parse_structured_review  # noqa: E402

OBS = re.compile(r"observab|metric|logging|\blog\b|monitor|telemetry|instrument|alert", re.I)
MONEY = re.compile(r"monetar|floating[- ]?point|rounding|decimal|currency|\bmoney\b|cents?\b", re.I)
UNDEF = re.compile(r"enqueue_digest_job|DigestScheduler", re.I)
USPEC = re.compile(r"error handling|retr(y|ies)|backoff", re.I)
BADCRIT = re.compile(r"contradict|bypass|self[- ]?serv|in tension|criterion 3|third criterion|conflict|inconsistent", re.I)
EH_FLAG = re.compile(r"error handling|retr(y|ies)|transient|idempoten|no explicit|unverified|hedge|defer", re.I)


@functools.lru_cache(maxsize=None)
def _read_review_file(path_str):
    p = pathlib.Path(path_str)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def review(mode, label):
    p = HERE / "runs" / mode / f"{label}-review.md"
    return _read_review_file(str(p))


@functools.lru_cache(maxsize=None)
def findings(txt):
    return parse_structured_review(txt) or []


def ftext(fs):
    return " ".join(f.get("description", "") + " " + f.get("recommendation", "") for f in fs)


def score_baseline():
    for label in ("std-sonnet", "std-codex", "domain", "adversarial"):
        txt = review("baseline", label)
        if not txt:
            print(f"{label:12s}: NO OUTPUT"); continue
        fs = findings(txt)
        nb = sum(1 for x in fs if x.get("severity") == "blocking")
        verdict = _parse_verdict(None, text=txt) or "(no VERDICT line)"
        obs = "obs✓" if OBS.search(ftext(fs)) else "obs✗"
        print(f"{label:12s}: {verdict[:30]:30s} blocking={nb} nonblk={len(fs)-nb} {obs} parse={'ok' if fs else 'EMPTY'}")


def score_microtest(reps=5):
    def col(bat, arm, fn):
        return [fn(review("microtest", f"{bat}-{arm}-{r}")) for r in range(1, reps + 1)]

    print("L-OBS — finding flags observability:")
    for arm in ("control", "treat"):
        hits = col("obs", arm, lambda t: bool(OBS.search(ftext(findings(t)))))
        print(f"  {arm:7s}: {sum(hits)}/{reps} {hits}")

    print("F4 — finding-count variance + money-anchor leak:")
    for arm in ("control", "treat"):
        cs = col("ex", arm, lambda t: len(findings(t)))
        an = col("ex", arm, lambda t: bool(MONEY.search(ftext(findings(t)))))
        print(f"  {arm:7s}: counts={cs} sd={statistics.pstdev(cs):.2f} anchor-leak={sum(an)}/{reps}")

    print("L-SEV — seam classification (B/N/-):")
    def cls(t, rx):
        fs = findings(t)
        b = any(rx.search(f.get("description", "") + f.get("recommendation", "")) for f in fs if f.get("severity") == "blocking")
        n = any(rx.search(f.get("description", "") + f.get("recommendation", "")) for f in fs if f.get("severity") != "blocking")
        return "B" if b else ("N" if n else "-")
    for arm in ("control", "treat"):
        u = col("sev", arm, lambda t: cls(t, UNDEF))
        s = col("sev", arm, lambda t: cls(t, USPEC))
        print(f"  {arm:7s}: UNDEF {u} | UNSPEC {s}")

    print("F2 — Pass B challenges planted bad criterion (PRESCREEN — read matches):")
    for arm in ("control", "treat"):
        h = col("f2", arm, lambda t: bool(BADCRIT.search(t)))
        print(f"  {arm:7s}: {sum(h)}/{reps} {h}")

    print("F3 — adversarial flags deferred error handling (PRESCREEN — read matches):")
    for arm in ("control", "treat"):
        h = col("f3", arm, lambda t: any(EH_FLAG.search(f.get("description", "") + f.get("recommendation", "")) for f in findings(t)))
        print(f"  {arm:7s}: {sum(h)}/{reps} {h}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    if mode == "baseline":
        score_baseline()
    elif mode == "microtest":
        score_microtest(int(sys.argv[2]) if len(sys.argv) > 2 else 5)
    else:
        sys.exit(f"unknown mode: {mode!r}")
