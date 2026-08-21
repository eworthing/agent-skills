#!/usr/bin/env python3
"""Post-hoc gate sweep over a target repo's contest-refactor artifact history.

Read-only against the target repo: every artifact state is materialized from git
blobs into a temp dir and validated by subprocessing the SHIPPED
validate-artifact.py — never a reimplementation (the item-16 acceptance rule).

Interpretation rule (write it into every report): a strict failure on an
artifact written before a gate shipped is an EPOCH OBSERVATION, not a violation
by the run. This sweep exists to collect the empirical phase-to-gate matrix
(which gates fail at which artifact states) for the Tier-3 validator design,
plus report-only diagnostics (G17 lines) and blind lines.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

ARTIFACT_FILES = (
    "CURRENT_REVIEW.json",
    "CURRENT_REVIEW.md",
    "REVIEW_HISTORY.json",
    "REVIEW_HISTORY.md",
    "findings_registry.json",
    "LOOP_STATE.json",
)

DEFAULT_VALIDATOR = (
    Path(__file__).resolve().parents[3] / "contest-refactor" / "scripts" / "validate-artifact.py"
)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True)


def sweep(repo: Path, validator: Path) -> list[dict]:
    log = _git(repo, "log", "--reverse", "--format=%H%x09%cI%x09%s", "--", "CURRENT_REVIEW.json")
    if log.returncode != 0:
        raise SystemExit(f"git log failed: {log.stderr.decode(errors='replace').strip()}")
    rows: list[dict] = []
    for line in log.stdout.decode(errors="replace").splitlines():
        commit, date, subject = line.split("\t", 2)
        with tempfile.TemporaryDirectory(prefix="posthoc-sweep-") as td_s:
            td = Path(td_s)
            present = []
            for name in ARTIFACT_FILES:
                show = _git(repo, "show", f"{commit}:{name}")
                if show.returncode == 0:
                    (td / name).write_bytes(show.stdout)
                    present.append(name)
            row: dict = {"commit": commit, "date": date, "subject": subject, "files": present}
            if "CURRENT_REVIEW.json" not in present:
                row["purged"] = True
                rows.append(row)
                continue
            try:
                art = json.loads((td / "CURRENT_REVIEW.json").read_text())
                for k in ("schema_version", "loop", "run_id", "state"):
                    row[k] = art.get(k)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                row["parse_error"] = str(exc)[:160]
            sidecar = td / "_issues.json"
            proc = subprocess.run(
                [sys.executable, str(validator), td_s, "--mode", "strict", "--json", str(sidecar)],
                capture_output=True,
                text=True,
            )
            row["exit"] = proc.returncode
            try:
                row["issues"] = json.loads(sidecar.read_text()).get("issues", [])
            except (OSError, json.JSONDecodeError):
                row["issues"] = []
                row["sidecar_error"] = True
            # Report-only diagnostics and blind lines print in [bracketed] form.
            row["diagnostics"] = [ln for ln in proc.stdout.splitlines() if ln.startswith("[")]
        rows.append(row)
    return rows


def to_markdown(repo: Path, rows: list[dict]) -> str:
    out = [
        f"# Post-hoc gate sweep — {repo}",
        "",
        "> Interpretation: strict failures on artifacts written before a gate shipped are",
        "> epoch observations, not violations by the run. This is phase-to-gate matrix data",
        "> for the Tier-3 validator design.",
        "",
        "| commit | date | loop | state | run_id | issues (rules) | diagnostics |",
        "|---|---|---|---|---|---|---|",
    ]
    rule_totals: Counter[str] = Counter()
    diag_totals: Counter[str] = Counter()
    for r in rows:
        if r.get("purged"):
            out.append(f"| {r['commit'][:9]} | {r['date'][:10]} | — | purged | — | — | — |")
            continue
        rules = Counter(i.get("rule", "?") for i in r.get("issues", []))
        rule_totals.update(rules)
        diags = [d.split()[0].strip("[]") for d in r.get("diagnostics", [])]
        diag_totals.update(diags)
        rule_s = ", ".join(f"{k}x{v}" if v > 1 else k for k, v in sorted(rules.items())) or "clean"
        diag_s = ", ".join(sorted(set(diags))) or "—"
        out.append(
            f"| {r['commit'][:9]} | {r['date'][:10]} | {r.get('loop')} | {r.get('state')} "
            f"| {r.get('run_id') or 'null'} | {rule_s} | {diag_s} |"
        )
    out += ["", "## Aggregate: issues by rule", ""]
    out += [f"- {k}: {v}" for k, v in rule_totals.most_common()]
    out += ["", "## Aggregate: bracketed diagnostics", ""]
    out += [f"- {k}: {v}" for k, v in diag_totals.most_common()]
    out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repo", type=Path)
    ap.add_argument("--validator", type=Path, default=DEFAULT_VALIDATOR)
    ap.add_argument("--out-json", type=Path)
    ap.add_argument("--out-md", type=Path)
    args = ap.parse_args()
    rows = sweep(args.repo.resolve(), args.validator.resolve())
    md = to_markdown(args.repo.resolve(), rows)
    if args.out_json:
        args.out_json.write_text(
            json.dumps({"repo": str(args.repo.resolve()), "rows": rows}, indent=1) + "\n"
        )
    if args.out_md:
        args.out_md.write_text(md)
    else:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
