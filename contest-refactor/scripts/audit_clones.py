#!/usr/bin/env python3
"""audit_clones.py — candidate-evidence detector for near-duplicate function bodies.

Signal for root causes S6/S7/R1 in the motivating audit (duplicate lock-guarded
arbiters reimplemented in multiple places instead of factored once). Same doctrine
tier as `audit_boundaries.py` and `audit_cochange.py`: output is **candidate evidence
for the Critic** — NOT a finding by itself, NOT a score input, and NOT a loop gate.
Every reported pair carries `promotion_allowed: false` (stated in the doctrine note
printed alongside the table, not as a literal per-row field — this repo's advisory
scripts state the doctrine textually).

Algorithm (see the section comments below for detail on each stage):
  1. Stdlib-only tokenizer: identifiers -> generic `ID`, string/number literals ->
     generic `LIT`, comments and whitespace stripped. This lets renamed-identifier
     clones (same structure, different variable names) still match.
  2. Per-language function-body extraction:
       - Swift/Kotlin: brace-counting from each `func`/`fun` declaration (tracks
         paren depth so a closure-typed default-parameter brace, e.g.
         `func f(cb: () -> Void = { ... })`, is not mistaken for the body's own
         opening brace). Approximate, not a real parser — adequate for
         candidate evidence.
       - Python: indentation-based (a `def` line's body is every subsequent
         line indented further than the `def`, until indentation returns to
         <= the `def`'s own level).
       - All other stacks: unsupported. Emit nothing, exit 0 — mirrors
         `audit_boundaries.py`'s "supported stacks: X only in v1, others emit
         nothing" framing. Never fabricate results for a language this tool
         doesn't parse.
  3. Winnowing / k-gram fingerprinting over each body's normalized token stream
     (the Winnowing algorithm: hash every k-token window, then keep only the
     local-minimum hash per w-window of those hashes — this bounds fingerprint
     volume while still guaranteeing any token run >= k + w - 1 shared between
     two bodies produces at least one shared fingerprint). k=5 token grams,
     w=4 winnow window: a defensible default for a candidate-evidence heuristic,
     not a tuned production clone-detector — no parameter search was run.
  4. Similarity: Jaccard overlap of the two fingerprint sets. A pair is reported
     when similarity >= 0.85 AND the smaller of the two bodies has >= 8 lines
     (the size floor matters because short bodies — trivial getters, one-line
     guards — produce noisy high-similarity scores on tiny fingerprint sets;
     that noise is exactly what the floor exists to cut).
  5. Ranking: reported pairs are ordered by similarity * average_lines,
     descending (favors larger, more-similar clusters over tiny near-duplicates).

FALSE-POSITIVE WARNING — read before trusting a row: SwiftUI view bodies are
structurally repetitive by nature (`VStack { Text(...); Button(...) }`-shaped
boilerplate is common to any two unrelated views, not just real duplicates). A
high similarity score on two `body: some View` implementations is NOT by itself
evidence of behavior-bearing duplication. The Critic must read both bodies and
confirm the duplication is actual logic (a lock-guarded arbiter, a computation,
a business rule) — not incidental structural similarity from the UI framework —
before promoting any pair to a finding.

Usage:
    audit_clones.py [<repo-dir>]

Exit codes:
  0 = ran (with or without candidate pairs, or unsupported-stack-empty)
  2 = usage error (bad path)
"""

from __future__ import annotations

import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MIN_SIMILARITY = 0.85
_MIN_LINES = 8
_KGRAM_SIZE = 5  # tokens per shingle — see module docstring stage 3
_WINNOW_WINDOW = 4  # winnow window — see module docstring stage 3

_SWIFT_KOTLIN_EXTS = frozenset({".swift", ".kt", ".kts"})
_PYTHON_EXTS = frozenset({".py"})

IGNORE_DIRS = frozenset(
    {
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        "env",
        "build",
        "dist",
        ".build",
        "DerivedData",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        "site-packages",
    }
)

# Keywords retained as literal tokens (not folded into the generic ID token) so
# control-flow / declaration structure survives normalization. Swift + Kotlin +
# Python keyword sets, unioned — a little cross-language slop here is harmless
# since a keyword from one language never appears as an identifier collision
# worth caring about in the other.
_KEYWORDS = frozenset(
    {
        # Swift
        "func",
        "let",
        "var",
        "if",
        "else",
        "for",
        "while",
        "return",
        "switch",
        "case",
        "default",
        "struct",
        "class",
        "enum",
        "protocol",
        "extension",
        "guard",
        "break",
        "continue",
        "in",
        "try",
        "catch",
        "throw",
        "throws",
        "import",
        "private",
        "public",
        "internal",
        "fileprivate",
        "static",
        "final",
        "override",
        "init",
        "deinit",
        "self",
        "super",
        "nil",
        "true",
        "false",
        "as",
        "is",
        "where",
        "repeat",
        "do",
        "defer",
        "typealias",
        "associatedtype",
        "some",
        "any",
        "async",
        "await",
        "actor",
        "inout",
        "mutating",
        "lazy",
        # Kotlin (delta over the Swift set above)
        "fun",
        "val",
        "when",
        "object",
        "interface",
        "companion",
        "package",
        "null",
        "this",
        "by",
        "out",
        "reified",
        "sealed",
        "data",
        "open",
        "abstract",
        "suspend",
        # Python (delta over the above)
        "def",
        "elif",
        "not",
        "and",
        "or",
        "lambda",
        "yield",
        "with",
        "from",
        "global",
        "nonlocal",
        "pass",
        "raise",
        "assert",
        "del",
        "None",
        "True",
        "False",
    }
)


@dataclass
class FunctionBody:
    """One extracted function: its source location and un-normalized body text."""

    file: Path
    start_line: int  # 1-based, the declaration line
    end_line: int  # 1-based, last line of the body
    text: str  # raw source text of the body (between braces, or the indented block)


@dataclass
class ExtractedFunction:
    """A FunctionBody after tokenization + fingerprinting, ready for pairwise scoring."""

    file: Path
    start_line: int
    lines: int
    fingerprint: set[int]


# ---------------------------------------------------------------------------
# Stage 1: tokenizer
# ---------------------------------------------------------------------------

# Single master regex drives both masking (stage 2's brace/indent search needs
# comments and string contents blanked out so braces or colons inside a string
# literal don't corrupt extraction) and normalization (stage 3's token stream).
_TOKEN_RE = re.compile(
    r"""
      (?P<BLOCK_COMMENT>/\*.*?\*/)
    | (?P<LINE_COMMENT>//[^\n]*|\#[^\n]*)
    | (?P<TRIPLE_STRING>\"\"\"(?:\\.|[^\\])*?\"\"\"|'''(?:\\.|[^\\])*?''')
    | (?P<STRING>"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*')
    | (?P<NUMBER>\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b)
    | (?P<IDENT>[A-Za-z_][A-Za-z0-9_]*)
    | (?P<NEWLINE>\n)
    | (?P<WS>[ \t]+)
    | (?P<OP>[^\sA-Za-z0-9_])
    """,
    re.VERBOSE | re.DOTALL,
)

_LITERAL_KINDS = frozenset({"STRING", "TRIPLE_STRING", "NUMBER"})
_SKIP_KINDS = frozenset({"BLOCK_COMMENT", "LINE_COMMENT", "NEWLINE", "WS"})


def _mask(text: str) -> str:
    """Blank out comment/string contents (preserving length + newlines).

    Used only to make brace/indent structure searches immune to braces, colons,
    or quote characters that happen to appear inside a string literal or comment.
    """
    out = list(text)
    for m in _TOKEN_RE.finditer(text):
        if m.lastgroup in ("BLOCK_COMMENT", "LINE_COMMENT", "STRING", "TRIPLE_STRING"):
            start, end = m.span()
            for i in range(start, end):
                if out[i] != "\n":
                    out[i] = " "
    return "".join(out)


def _normalize_tokens(text: str) -> list[str]:
    """Source text -> normalized token stream (ID / LIT / keyword / operator)."""
    tokens: list[str] = []
    for m in _TOKEN_RE.finditer(text):
        kind = m.lastgroup
        if kind in _SKIP_KINDS:
            continue
        if kind in _LITERAL_KINDS:
            tokens.append("LIT")
        elif kind == "IDENT":
            val = m.group()
            tokens.append(val if val in _KEYWORDS else "ID")
        else:  # OP — a single punctuation/operator character, kept as itself
            tokens.append(m.group())
    return tokens


# ---------------------------------------------------------------------------
# Stage 2: per-language function-body extraction
# ---------------------------------------------------------------------------

_FUNC_DECL_RE = re.compile(r"\b(?:func|fun)\s+[A-Za-z_][A-Za-z0-9_]*")
_DEF_RE = re.compile(r"^([ \t]*)def\s+[A-Za-z_][A-Za-z0-9_]*", re.MULTILINE)

# How far past a func/fun declaration to look for its opening brace before
# giving up (a protocol/abstract method has no body at all — without this cap
# a body-less declaration would wrongly latch onto a later, unrelated brace).
_MAX_BODY_LOOKAHEAD = 400


def _extract_swift_kotlin_functions(path: Path, text: str) -> list[FunctionBody]:
    masked = _mask(text)
    n = len(masked)
    functions: list[FunctionBody] = []

    for m in _FUNC_DECL_RE.finditer(masked):
        # Scan forward tracking paren depth so a closure-typed default-parameter
        # brace (e.g. `= { ... }` inside the parameter list) is not mistaken for
        # the function's own opening brace, which only appears at paren depth 0.
        i = m.end()
        limit = min(n, m.end() + _MAX_BODY_LOOKAHEAD)
        paren_depth = 0
        brace_start: int | None = None
        while i < limit:
            c = masked[i]
            if c == "(":
                paren_depth += 1
            elif c == ")":
                paren_depth = max(0, paren_depth - 1)
            elif c == "{" and paren_depth == 0:
                brace_start = i
                break
            i += 1
        if brace_start is None:
            continue  # protocol/abstract declaration — no body

        depth = 0
        j = brace_start
        close_idx: int | None = None
        while j < n:
            if masked[j] == "{":
                depth += 1
            elif masked[j] == "}":
                depth -= 1
                if depth == 0:
                    close_idx = j
                    break
            j += 1
        if close_idx is None:
            continue  # unbalanced braces (shouldn't happen on valid source) — skip defensively

        body_text = text[brace_start + 1 : close_idx]
        start_line = text.count("\n", 0, m.start()) + 1
        end_line = text.count("\n", 0, close_idx) + 1
        functions.append(FunctionBody(path, start_line, end_line, body_text))

    return functions


def _extract_python_functions(path: Path, text: str) -> list[FunctionBody]:
    masked = _mask(text)
    lines = text.splitlines()
    masked_lines = masked.splitlines()
    n = len(lines)
    functions: list[FunctionBody] = []

    for m in _DEF_RE.finditer(masked):
        def_indent = len(m.group(1))
        start_line_idx = masked.count("\n", 0, m.start())  # 0-based
        end_line_idx = start_line_idx
        i = start_line_idx + 1
        while i < n:
            masked_stripped = masked_lines[i].strip() if i < len(masked_lines) else ""
            if masked_stripped == "":
                # blank or comment-only line — doesn't itself extend the body,
                # but doesn't end it either (could be a gap inside the function)
                i += 1
                continue
            raw = lines[i]
            indent = len(raw) - len(raw.lstrip(" \t"))
            if indent > def_indent:
                end_line_idx = i
                i += 1
                continue
            break

        if end_line_idx == start_line_idx:
            continue  # no indented body found (e.g. a body-less stub) — skip

        body_text = "\n".join(lines[start_line_idx + 1 : end_line_idx + 1])
        functions.append(FunctionBody(path, start_line_idx + 1, end_line_idx + 1, body_text))

    return functions


def _collect_files(root: Path, exts: frozenset[str]) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in exts:
            continue
        rel_parts = path.relative_to(root).parts
        if any(part in IGNORE_DIRS for part in rel_parts[:-1]):
            continue
        files.append(path)
    return sorted(files)


def _extract_all_functions(root: Path) -> list[FunctionBody]:
    functions: list[FunctionBody] = []
    for path in _collect_files(root, _SWIFT_KOTLIN_EXTS):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        functions.extend(_extract_swift_kotlin_functions(path, text))
    for path in _collect_files(root, _PYTHON_EXTS):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        functions.extend(_extract_python_functions(path, text))
    return functions


# ---------------------------------------------------------------------------
# Stage 3: winnowing / k-gram fingerprinting
# ---------------------------------------------------------------------------


def _hash_gram(tokens: list[str]) -> int:
    joined = "\x1f".join(tokens)
    return int(hashlib.sha1(joined.encode("utf-8")).hexdigest()[:16], 16)


def _fingerprint(tokens: list[str]) -> set[int]:
    """Winnowed k-gram fingerprint set for a normalized token stream."""
    if len(tokens) < _KGRAM_SIZE:
        return set()

    hashes = [_hash_gram(tokens[i : i + _KGRAM_SIZE]) for i in range(len(tokens) - _KGRAM_SIZE + 1)]
    if len(hashes) <= _WINNOW_WINDOW:
        return set(hashes)  # too short for a full winnow window — keep every gram

    fp: set[int] = set()
    for i in range(len(hashes) - _WINNOW_WINDOW + 1):
        window = hashes[i : i + _WINNOW_WINDOW]
        min_val = min(window)
        # Rightmost-minimum tie-break — the standard winnowing convention,
        # which avoids over-selecting on runs of identical hashes.
        min_idx = max(idx for idx, v in enumerate(window) if v == min_val)
        fp.add(window[min_idx])
    return fp


# ---------------------------------------------------------------------------
# Stage 4+5: similarity scoring + ranking
# ---------------------------------------------------------------------------


def _jaccard(a: set[int], b: set[int]) -> float:
    if not a or not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def _to_extracted(bodies: list[FunctionBody]) -> list[ExtractedFunction]:
    extracted: list[ExtractedFunction] = []
    for fb in bodies:
        tokens = _normalize_tokens(fb.text)
        fp = _fingerprint(tokens)
        if not fp:
            continue
        lines = fb.end_line - fb.start_line + 1
        extracted.append(ExtractedFunction(fb.file, fb.start_line, lines, fp))
    return extracted


def _find_pairs(
    bodies: list[FunctionBody],
) -> list[tuple[ExtractedFunction, ExtractedFunction, float]]:
    extracted = _to_extracted(bodies)
    pairs: list[tuple[ExtractedFunction, ExtractedFunction, float]] = []

    for i in range(len(extracted)):
        for j in range(i + 1, len(extracted)):
            a, b = extracted[i], extracted[j]
            if a.file == b.file and a.start_line == b.start_line:
                continue
            size = min(a.lines, b.lines)
            if size < _MIN_LINES:
                continue
            sim = _jaccard(a.fingerprint, b.fingerprint)
            if sim >= _MIN_SIMILARITY:
                pairs.append((a, b, sim))

    pairs.sort(key=lambda t: -(t[2] * ((t[0].lines + t[1].lines) / 2)))
    return pairs


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def _format_md(root: Path, pairs: list[tuple[ExtractedFunction, ExtractedFunction, float]]) -> str:
    lines = [
        "# Clone-Candidate Report",
        "",
        "> **CANDIDATE EVIDENCE ONLY** — not a finding. Confirm duplication is",
        "> behavior-bearing (real logic, not incidental structural boilerplate —",
        "> SwiftUI view bodies especially) before promoting any pair below.",
        "",
        "| file:line a | file:line b | lines | similarity |",
        "|---|---|---|---|",
    ]
    for a, b, sim in pairs:
        a_loc = f"{a.file.relative_to(root)}:{a.start_line}"
        b_loc = f"{b.file.relative_to(root)}:{b.start_line}"
        size = min(a.lines, b.lines)
        lines.append(f"| {a_loc} | {b_loc} | {size} | {sim:.2f} |")
    lines += [
        "",
        f"_{len(pairs)} candidate pair(s). promotion_allowed: false for all rows above —_",
        "_the Critic decides whether the duplication is real._",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv if argv is None else argv
    root = Path(argv[1]).resolve() if len(argv) > 1 else Path.cwd()
    if not root.is_dir():
        print(f"audit_clones: not a directory: {root}", file=sys.stderr)
        return 2

    bodies = _extract_all_functions(root)
    if not bodies:
        print(
            "audit_clones: no Swift/Kotlin/Python function bodies found "
            "(supported stacks: Swift, Kotlin, Python; others emit nothing)",
            file=sys.stderr,
        )
        return 0

    pairs = _find_pairs(bodies)
    if not pairs:
        print("audit_clones: no clone candidates at or above threshold", file=sys.stderr)
        return 0

    print(_format_md(root, pairs))
    print(
        f"\n{len(pairs)} clone-candidate pair(s) — candidate evidence for the Critic; "
        "not a finding by itself and not a loop gate. Verify duplication is "
        "behavior-bearing before promoting (SwiftUI view bodies are structurally "
        "repetitive by nature — raw similarity on UI code is not evidence of real "
        "duplication).",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
