#!/usr/bin/env python3
"""validate_portability.py - Static analyzer for macOS Bash 3.2 and BSD portability.

Scans shell scripts for Bash 4+ syntax and GNU-specific coreutils flags that
fail on stock macOS (/bin/bash 3.2.57, BSD userland). Zero external dependencies.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Finding:
    file: str
    line_number: int
    line_content: str
    rule_id: str
    message: str
    suggestion: str
    severity: str = "error"


RULES: list[dict[str, str]] = [
    {
        "id": "bash4-assoc-array",
        "pattern": r"\bdeclare\s+(?:-\w*A\w*)\b",
        "message": "Associative arrays ('declare -A') require Bash 4.0+",
        "suggestion": "Use indexed arrays, case statements, or lookup functions",
    },
    {
        "id": "bash4-mapfile",
        "pattern": r"\b(?:mapfile|readarray)\b",
        "message": "'mapfile' and 'readarray' require Bash 4.0+",
        "suggestion": "Use 'while IFS= read -r line; do ... done < file' loop",
    },
    {
        "id": "bash4-case-modification",
        "pattern": r"\$\{[^}]*(?:,,|\^\^)[^}]*\}",
        "message": "Case modification operators ('${var,,}', '${var^^}') require Bash 4.0+",
        "suggestion": 'Use \'printf "%s" "$var" | tr "[:upper:]" "[:lower:]"\'',
    },
    {
        "id": "bash4-globstar",
        "pattern": r"\bshopt\s+-[sq]\s+globstar\b",
        "message": "'shopt -s globstar' is not supported in Bash 3.2",
        "suggestion": "Use 'find' with '-name' and '-print0' loop",
    },
    {
        "id": "bash4-pipe-stderr",
        "pattern": r"\|\&",
        "message": "Pipe stderr shorthand ('|&') requires Bash 4.0+",
        "suggestion": "Use '2>&1 |' instead",
    },
    {
        "id": "bash4-coproc",
        "pattern": r"\bcoproc\b",
        "message": "'coproc' requires Bash 4.0+",
        "suggestion": "Use named pipes ('mkfifo') or subshell jobs",
    },
    {
        "id": "bash4-wait-n",
        "pattern": r"\bwait\s+-n\b",
        "message": "'wait -n' requires Bash 4.3+",
        "suggestion": "Use standard 'wait' or job monitoring loop",
    },
    {
        "id": "bash4-nameref",
        "pattern": r"\b(?:local|declare)\s+-\w*n\w*\b",
        "message": "Namerefs ('local -n') require Bash 4.3+",
        "suggestion": "Pass variable names and use explicit indirection or structured functions",
    },
    {
        "id": "gnu-sed-r",
        "pattern": r"\bsed\s+-[a-zA-Z]*r",
        "message": "GNU 'sed -r' is not supported on BSD sed",
        "suggestion": "Use 'sed -E' for portable extended regular expressions",
    },
    {
        "id": "gnu-grep-pcre",
        "pattern": r"\bgrep\s+-[a-zA-Z]*P",
        "message": "GNU 'grep -P' (PCRE) is not supported on BSD grep",
        "suggestion": "Use 'grep -E' with POSIX extended regular expressions",
    },
    {
        "id": "gnu-date-d",
        "pattern": r"\bdate\s+-[a-zA-Z]*d\b",
        "message": "GNU 'date -d' is not supported on BSD date",
        "suggestion": "Use BSD 'date -v' (e.g. 'date -v-7d +%s') or epoch arithmetic",
    },
    {
        "id": "gnu-stat-c",
        "pattern": r"\bstat\s+-[a-zA-Z]*c\b",
        "message": "GNU 'stat -c' format syntax is not supported on BSD stat",
        "suggestion": "Use BSD 'stat -f' (e.g. 'stat -f %z' for size) or portable awk/wc",
    },
    {
        "id": "gnu-base64-w",
        "pattern": r"\bbase64\s+-[a-zA-Z]*w\b",
        "message": "GNU 'base64 -w' is not supported on BSD base64",
        "suggestion": "Use 'base64 | tr -d \"\\n\"' for unwrapped output",
    },
    {
        "id": "pattern-local-assignment-split",
        "pattern": r"^\s*(?:local|declare|readonly|export)\s+[A-Za-z_][A-Za-z0-9_]*=\$\(",
        "message": "Combining 'local' declaration with command substitution masks exit status under 'set -e'",
        "suggestion": "Separate declaration from assignment: 'local x; x=\"$(cmd)\"'",
    },
    {
        "id": "pattern-array-length-default",
        "pattern": r"\$\{#\w+\[@\]:-",
        "message": "'${#arr[@]:-default}' does not protect against unbound variable errors on Bash 3.2",
        "suggestion": "Declare the array empty before use ('arr=()') or use '${arr[@]+\"${arr[@]}\"}'",
    },
]

COMPILED_RULES = [
    (
        rule["id"],
        re.compile(rule["pattern"]),
        rule["message"],
        rule["suggestion"],
    )
    for rule in RULES
]


def scan_file(file_path: Path) -> list[Finding]:
    findings: list[Finding] = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as err:
        return [
            Finding(
                file=str(file_path),
                line_number=0,
                line_content="",
                rule_id="io-error",
                message=f"Failed to read file: {err}",
                suggestion="Check file permissions and path",
            )
        ]

    for line_idx, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        for rule_id, pattern, message, suggestion in COMPILED_RULES:
            if pattern.search(line):
                findings.append(
                    Finding(
                        file=str(file_path),
                        line_number=line_idx,
                        line_content=line,
                        rule_id=rule_id,
                        message=message,
                        suggestion=suggestion,
                    )
                )

    return findings


def scan_paths(paths: list[Path]) -> list[Finding]:
    all_findings: list[Finding] = []
    for path in paths:
        if path.is_file():
            if path.suffix == ".sh" or path.name.endswith(".sh"):
                all_findings.extend(scan_file(path))
            else:
                # Check if file has a bash/sh shebang
                try:
                    with path.open("r", encoding="utf-8", errors="replace") as f:
                        first_line = f.readline()
                        if first_line.startswith("#!") and (
                            "bash" in first_line or "sh" in first_line
                        ):
                            all_findings.extend(scan_file(path))
                except OSError:
                    pass
        elif path.is_dir():
            for sh_file in path.rglob("*.sh"):
                all_findings.extend(scan_file(sh_file))
    return all_findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan shell scripts for macOS Bash 3.2 and BSD incompatibilities."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="One or more shell script files or directories to scan",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output findings in structured JSON format",
    )
    args = parser.parse_args()

    findings = scan_paths(args.paths)

    if args.json:
        output = {
            "total_violations": len(findings),
            "clean": len(findings) == 0,
            "findings": [asdict(f) for f in findings],
        }
        print(json.dumps(output, indent=2))
    else:
        if not findings:
            print(f"✓ Scanned {len(args.paths)} path(s). No portability issues found.")
            return 0

        print(f"✗ Found {len(findings)} portability issue(s):\n")
        for f in findings:
            print(f"  [{f.rule_id}] {f.file}:{f.line_number}")
            print(f"    Line:       {f.line_content.strip()}")
            print(f"    Issue:      {f.message}")
            print(f"    Suggestion: {f.suggestion}\n")

    return 0 if len(findings) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
