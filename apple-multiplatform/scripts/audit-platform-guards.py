#!/usr/bin/env python3
"""audit-platform-guards.py — Static audit for cross-platform guard mistakes.

Reports a symbol only when the enclosing `#if` guard stack proves the line is
actually compiled for the offending platform. A file-scoped grep cannot do this:
`#if os(tvOS)` excludes macOS without ever naming it, so "does the string
`os(macOS)` appear in this file?" flags every correctly-guarded tvOS-only file.

Build-break checks (exit 1):

  T1  tvOS-unavailable UIKit symbols (haptics, UIPasteboard) on a tvOS-compiled line
  T1b .onDrop / DropDelegate on a tvOS-compiled line (SwiftUI, not UIKit — no tvOS)
  T2  @Environment(\\.editMode) on a macOS-compiled line
  T3  .tabViewStyle(.page) on a macOS-compiled line
  T4  .topBarLeading / .topBarTrailing on a macOS-compiled line
  T5  .fullScreenCover on a macOS-compiled line

Dead-code checks (informational, do NOT affect exit code):

  D1  editMode compiles on tvOS and nothing in the tree injects it — dead code.
      Suppressed tree-wide if any tvOS-compiled line does
      `.environment(\\.editMode, …)`: an app may legitimately own that channel.
  D2  .topBar* compiles on tvOS — symbol exists (tvOS 14+), but no top-bar chrome

Output:
  APPLE-MP-FAIL <platform> <error-class> <file>:<line>: <message>
  APPLE-MP-INFO <platform> <code> <file>:<line>: <message>

Exit status: 0 = no build-break hits, 1 = one or more, 2 = usage error.

Requires python3 (ships with the Xcode command line tools). Stdlib only.
`#if` conditions are untrusted input from the scanned repo, so they are parsed,
never eval()'d.
"""

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------- conditions


class Cond:
    """Parsed `#if` condition. Evaluated against a platform assignment."""

    def __init__(self, kind, *args):
        self.kind = kind  # 'term' | 'not' | 'and' | 'or'
        self.args = args

    def eval(self, env):
        if self.kind == "term":
            return _eval_term(self.args[0], env)
        if self.kind == "not":
            return not self.args[0].eval(env)
        if self.kind == "and":
            return self.args[0].eval(env) and self.args[1].eval(env)
        if self.kind == "or":
            return self.args[0].eval(env) or self.args[1].eval(env)
        raise AssertionError(f"unknown cond kind: {self.kind}")


def _eval_term(term, env):
    """Evaluate one atom.

    Unknown atoms (DEBUG, swift(>=6.0), canImport(SomeOptionalFramework)) are
    True: assume the line compiles. That is the conservative direction for a
    linter — it may over-report, never under-report. It also makes compound
    conditions like `DEBUG && os(macOS)` evaluate correctly on tvOS.
    """
    m = re.match(r"^os\(\s*([A-Za-z]+)\s*\)$", term)
    if m:
        return m.group(1) == env["platform"]

    m = re.match(r"^targetEnvironment\(\s*([A-Za-z]+)\s*\)$", term)
    if m:
        return m.group(1) == "macCatalyst" and env["catalyst"]

    m = re.match(r"^canImport\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)$", term)
    if m:
        framework = m.group(1)
        if framework == "UIKit":
            # True on iOS, iPadOS, tvOS and Mac Catalyst; false on native macOS.
            return env["platform"] in ("iOS", "tvOS") or env["catalyst"]
        if framework == "AppKit":
            return env["platform"] == "macOS"
        return True  # unknown framework — assume importable

    return True  # DEBUG, swift(>=6.0), custom flags


class _Parser:
    """expr := or ; or := and ('||' and)* ; and := unary ('&&' unary)*
    unary := '!' unary | primary ; primary := '(' expr ')' | atom
    """

    def __init__(self, text):
        self.toks = self._lex(text)
        self.pos = 0

    @staticmethod
    def _lex(text):
        return re.findall(r"\|\||&&|!|\(|\)|[A-Za-z_][A-Za-z0-9_]*|[^\s()!&|]+", text)

    def _peek(self):
        return self.toks[self.pos] if self.pos < len(self.toks) else None

    def _next(self):
        tok = self._peek()
        self.pos += 1
        return tok

    def parse(self):
        node = self._or()
        return node if node else Cond("term", "unknown")

    def _or(self):
        node = self._and()
        while self._peek() == "||":
            self._next()
            node = Cond("or", node, self._and())
        return node

    def _and(self):
        node = self._unary()
        while self._peek() == "&&":
            self._next()
            node = Cond("and", node, self._unary())
        return node

    def _unary(self):
        if self._peek() == "!":
            self._next()
            return Cond("not", self._unary())
        return self._primary()

    def _primary(self):
        tok = self._next()
        if tok is None:
            return Cond("term", "unknown")
        if tok == "(":
            node = self._or()
            if self._peek() == ")":
                self._next()
            return node
        # An identifier optionally followed by a parenthesised argument list,
        # e.g. os(tvOS) / canImport(UIKit) / swift(>=6.0). Re-join into one atom.
        atom = tok
        if self._peek() == "(":
            depth = 0
            while self._peek() is not None:
                t = self._next()
                atom += t
                if t == "(":
                    depth += 1
                elif t == ")":
                    depth -= 1
                    if depth == 0:
                        break
        return Cond("term", atom)


def parse_cond(text):
    return _Parser(text.strip()).parse()


# ---------------------------------------------------------------- source prep


def strip_comments(lines):
    """Blank out // and /* */ comments, preserving line count and numbering.

    Known limitation: comment markers inside string literals are not
    special-cased. In practice a Swift line containing a literal "//" that must
    still match one of the audited symbols does not occur; the trade is worth
    the simplicity.
    """
    out = []
    in_block = False
    for line in lines:
        buf = []
        i = 0
        while i < len(line):
            two = line[i : i + 2]
            if in_block:
                if two == "*/":
                    in_block = False
                    i += 2
                    continue
                i += 1
                continue
            if two == "/*":
                in_block = True
                i += 2
                continue
            if two == "//":
                break
            buf.append(line[i])
            i += 1
        out.append("".join(buf))
    return out


def compiled_lines(lines, env):
    """Yield (lineno, text) for lines compiled under `env`, tracking #if state.

    `#elseif C` becomes NOT(previous branch condition) AND C, so a
    `#if os(tvOS) / #elseif os(macOS) / #else` chain resolves its `#else` to
    "neither tvOS nor macOS" — i.e. iOS. Getting this wrong is what makes
    hand-rolled scanners misreport three-way chains.
    """
    stack = []  # active condition per open #if
    seen = []  # disjunction of branches already taken per open #if
    for idx, raw in enumerate(lines, start=1):
        s = raw.strip()
        if s.startswith("#if "):
            cond = parse_cond(s[4:])
            stack.append(cond)
            seen.append(cond)
            continue
        if s.startswith("#elseif "):
            if stack:
                cond = parse_cond(s[8:])
                prior = seen[-1]
                stack[-1] = Cond("and", Cond("not", prior), cond)
                seen[-1] = Cond("or", prior, cond)
            continue
        if s.startswith("#else"):
            if stack:
                stack[-1] = Cond("not", seen[-1])
            continue
        if s.startswith("#endif"):
            if stack:
                stack.pop()
                seen.pop()
            continue
        if all(c.eval(env) for c in stack):
            yield idx, raw


# ---------------------------------------------------------------- the checks

MACOS = {"platform": "macOS", "catalyst": False}
TVOS = {"platform": "tvOS", "catalyst": False}

# (code, platform, env, compiled regex, message)
BUILD_CHECKS = [
    (
        "T1-canImport-vs-os",
        "tvOS",
        TVOS,
        re.compile(r"\bUI(?:Impact|Selection|Notification)FeedbackGenerator\b|\bUIPasteboard\b"),
        "UIKit symbol unavailable on tvOS — gate with #if os(iOS), not canImport(UIKit)",
    ),
    (
        "T1b-drop-receiving-tvos",
        "tvOS",
        TVOS,
        re.compile(r"\.onDrop\(|\bDropDelegate\b"),
        "drag-and-drop receiving is unavailable on tvOS — gate with #if !os(tvOS)",
    ),
    (
        "T2-editmode-macos",
        "macOS",
        MACOS,
        re.compile(r"@Environment\(\\\.editMode\)"),
        "editMode is unavailable on macOS — gate with #if os(iOS)",
    ),
    (
        "T3-tabview-page-unguarded",
        "macOS",
        MACOS,
        re.compile(r"\.tabViewStyle\(\s*\.page"),
        ".tabViewStyle(.page) is unavailable on macOS — use .automatic there",
    ),
    (
        "T4-topbar-placement-unguarded",
        "macOS",
        MACOS,
        re.compile(r"\.topBar(?:Leading|Trailing)\b"),
        ".topBarLeading/.topBarTrailing are unavailable on macOS — use a different placement",
    ),
    (
        "T5-fullscreencover-unguarded",
        "macOS",
        MACOS,
        re.compile(r"\.fullScreenCover\b"),
        ".fullScreenCover is unavailable on macOS — use .sheet there",
    ),
]

INFO_CHECKS = [
    (
        "D1-editmode-tvos-deadcode",
        "tvOS",
        TVOS,
        re.compile(r"@Environment\(\\\.editMode\)"),
        "editMode compiles on tvOS but nothing injects it — dead code; narrow to #if os(iOS)",
    ),
    (
        "D2-topbar-tvos-deadcode",
        "tvOS",
        TVOS,
        re.compile(r"\.topBar(?:Leading|Trailing)\b"),
        "topBar placement compiles on tvOS but there is no top-bar chrome — dead code; narrow to #if os(iOS)",
    ),
]

# Tree-level precondition for D1.
#
# "editMode is dead on tvOS" holds only while nothing supplies the value. An app
# may legitimately drive `\.editMode` itself on tvOS — injecting it with
# `.environment(\.editMode, $editMode)` and using it as its own multi-select
# channel — and then every tvOS reader of it is live, not dead. A real app does
# exactly this, and D1 reported it as dead code until this precondition existed.
# If any tvOS-compiled line in the tree injects editMode, D1 is suppressed
# tree-wide.
EDITMODE_INJECTION = re.compile(r"\.environment\(\s*\\\.editMode\b")

EXCLUDED_DIRS = {".git", ".build", "DerivedData"}


def _read_lines(path):
    try:
        return strip_comments(Path(path).read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError:
        return None


def tree_injects_editmode_on_tvos(paths):
    """True if any tvOS-compiled line supplies `\\.editMode` via .environment()."""
    for path in paths:
        lines = _read_lines(path)
        if lines is None:
            continue
        for _lineno, text in compiled_lines(lines, TVOS):
            if EDITMODE_INJECTION.search(text):
                return True
    return False


def audit_file(path, skip_codes=frozenset()):
    lines = _read_lines(path)
    if lines is None:
        return 0

    fails = 0

    for code, platform, env, pattern, message in BUILD_CHECKS:
        for lineno, text in compiled_lines(lines, env):
            if pattern.search(text):
                print(f"APPLE-MP-FAIL {platform} {code} {path}:{lineno}: {message}")
                fails += 1

    for code, platform, env, pattern, message in INFO_CHECKS:
        if code in skip_codes:
            continue
        for lineno, text in compiled_lines(lines, env):
            if pattern.search(text):
                print(f"APPLE-MP-INFO {platform} {code} {path}:{lineno}: {message}")

    return fails


def main(argv):
    if len(argv) > 2:
        sys.stderr.write(f"usage: {argv[0]} [path]\n  path defaults to the current directory.\n")
        return 2
    root = Path(argv[1] if len(argv) == 2 else ".")
    if not root.is_dir():
        sys.stderr.write(f"error: {root} is not a directory\n")
        return 2

    paths = [p for p in sorted(root.rglob("*.swift")) if not EXCLUDED_DIRS.intersection(p.parts)]

    skip_codes = set()
    if tree_injects_editmode_on_tvos(paths):
        skip_codes.add("D1-editmode-tvos-deadcode")

    fails = 0
    for path in paths:
        fails += audit_file(path, skip_codes)

    if fails:
        sys.stderr.write(
            f"\n{fails} hit(s). See apple-multiplatform/references/recovery.md for fixes.\n"
        )
        return 1

    print("No platform-guard issues found.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
