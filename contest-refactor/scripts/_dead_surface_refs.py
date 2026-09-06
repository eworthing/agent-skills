#!/usr/bin/env python3
"""_dead_surface_refs.py — lexical Swift structure parse + reference index for
audit_dead_surface.py.

Split into its own module to keep audit_dead_surface.py under the repo's
module-size soft cap (600 LoC); this is not a general-purpose API, just the
parsing/reference-counting half of that one scanner.

`//` and `/* */` comments are stripped before parsing AND before reference
counting (string literal contents are left alone -- see `strip_comments`).
Two reasons, both load-bearing:
  - a doc comment cross-referencing a sibling symbol (`` ``forTransport(_:)`` ``)
    would otherwise read as a use site and hide a genuinely dead symbol;
  - a commented-out `case`/`func` line would otherwise mint a phantom
    declaration that then pollutes the row list.

Reference counting is deliberately name-only, not type-qualified: two
unrelated types with a same-named member are indistinguishable to a lexical
scanner, and the design choice (spec, OCR-GAP-REMEDIATION-PLAN-2026-09-03 W2)
is to accept the false negative rather than risk a false positive --
"Shadowed or overloaded names: any occurrence of the bare name counts, so a
shadowed name is never flagged."
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_TYPE_RE = re.compile(
    r"^\s*(?P<mods>(?:(?:public|open|internal|private|fileprivate|final|indirect|"
    r"@\w+(?:\([^)]*\))?)\s+)*)"
    r"(?P<kind>struct|class|enum|actor|protocol|extension)\s+"
    r"(?P<name>[A-Za-z_]\w*)"
    r"(?P<rest>.*)$"
)
_PREVIEW_RE = re.compile(r"^\s*#Preview\b")
_CASE_RE = re.compile(r"^\s*(?:indirect\s+)?case\s+(?P<body>.+)$")
_CASE_ENTRY_RE = re.compile(r"^(?P<name>[A-Za-z_]\w*)")
_MEMBER_VAR_RE = re.compile(
    r"^\s*(?P<mods>(?:(?:public|open|internal|private|fileprivate|static|class|final|"
    r"lazy|weak|unowned(?:\([^)]*\))?|override|required|convenience|mutating|nonmutating|"
    r"@\w+(?:\([^)]*\))?)\s+)*)"
    r"(?:var|let)\s+(?P<name>[A-Za-z_]\w*)\b"
)
_MEMBER_FUNC_RE = re.compile(
    r"^\s*(?P<mods>(?:(?:public|open|internal|private|fileprivate|static|class|final|"
    r"mutating|nonmutating|override|required|convenience|@\w+(?:\([^)]*\))?)\s+)*)"
    r"func\s+(?P<name>[A-Za-z_]\w*)\s*(?:<[^>]*>)?\s*\("
)
_EXCLUDED_ATTRS = ("@objc", "@ibaction", "@iboutlet", "@main")
_IDENT_RE = re.compile(r"\b[A-Za-z_]\w*\b")
_ACCESS_KEYWORDS = ("public", "open", "internal", "private", "fileprivate")
_CASE_LET_TAIL_RE = re.compile(r"\b(?:if\s+)?case(?:\s+let)?\s*$")
_LET_TAIL_RE = re.compile(r"\blet\s*$")
_ASSOC_VALUE_RE = re.compile(r"^\([^)]*\)")


def strip_comments(text: str) -> str:
    """Blank out `//...` and `/* ... */` spans, preserving every other
    character's offset (line/column numbers stay exact for downstream regex
    matching). Does not look inside string literals for a comment opener --
    ponytail: a `"//"` inside a Swift string is rare, and the false trigger
    only ever deletes text (never adds a bogus declaration), so the failure
    mode is a missed member, not a phantom one."""
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        two = text[i : i + 2]
        if two == "//":
            j = text.find("\n", i)
            j = n if j == -1 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        elif two == "/*":
            j = text.find("*/", i + 2)
            j = n if j == -1 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
        else:
            i += 1
    return "".join(out)


def _blank_strings(text: str) -> str:
    """Blank out Swift string-literal contents (`"..."` and `\"\"\"...\"\"\"`),
    preserving every other character's offset (including newlines) so line
    numbers stay exact. Used only for the brace-depth pass, so a literal
    `{`/`}` inside a string can't corrupt TypeFrame nesting -- ponytail:
    interpolation (`\\(...)`) is treated as opaque string content, not
    parsed; full interpolation-aware parsing is out of scope here."""
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        if text[i : i + 3] == '"""':
            j = text.find('"""', i + 3)
            j = n if j == -1 else j + 3
        elif text[i] == '"':
            j = i + 1
            while j < n and text[j] not in ('"', "\n"):
                j += 2 if text[j] == "\\" and j + 1 < n else 1
            j = j + 1 if j < n and text[j] == '"' else j
        else:
            i += 1
            continue
        for k in range(i, j):
            if out[k] != "\n":
                out[k] = " "
        i = j
    return "".join(out)


def _access_of(mods: str, default: str = "internal") -> str:
    for kw in _ACCESS_KEYWORDS:
        if re.search(rf"\b{kw}\b", mods):
            return kw
    return default


def _has_excluded_attr(mods: str) -> bool:
    lower = mods.lower()
    return any(attr in lower for attr in _EXCLUDED_ATTRS)


def _parse_conformances(rest: str) -> set[str]:
    rest = re.sub(r"^\s*<[^>]*>", "", rest)
    if ":" not in rest:
        return set()
    after = rest.split(":", 1)[1]
    after = after.split("where", 1)[0]
    after = after.split("{", 1)[0]
    out: set[str] = set()
    for part in after.split(","):
        m = re.match(r"\s*([A-Za-z_]\w*)", part)
        if m:
            out.add(m.group(1))
    return out


def _split_top_level_commas(s: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    cur: list[str] = []
    for ch in s:
        if ch in "([<":
            depth += 1
        elif ch in ")]>":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    parts.append("".join(cur))
    return parts


def _is_pattern_position(line: str, dot_pos: int, name_end: int) -> bool:
    """True when a `.name` occurrence is a case-match, not a construction or
    read. Two shapes: `case .name` / `case let .name` / `if case .name` /
    a continuation's repeated `let .name` (`case let .a,\\n     let .b:`); and
    a continuation item that is the first thing on its line and is followed
    by `:` or `,` (`.name:` closing a switch arm, `.name,` mid-list, as in
    `case .a,\\n     .b:`)."""
    before = line[:dot_pos].rstrip()
    if _CASE_LET_TAIL_RE.search(before) or _LET_TAIL_RE.search(before):
        return True
    if before == "":
        after = _ASSOC_VALUE_RE.sub("", line[name_end:].lstrip())
        if after[:1] in (":", ","):
            return True
    return False


@dataclass
class MemberSig:
    line: int
    name: str
    access: str = "internal"


@dataclass
class TypeFrame:
    file: str
    kind: str  # struct|class|enum|actor|protocol|extension|preview
    name: str
    access: str
    conformances: set[str]
    is_preview: bool
    start_line: int
    end_line: int = 0
    members: list[MemberSig] = field(default_factory=list)
    cases: list[MemberSig] = field(default_factory=list)


@dataclass
class RawDecl:
    kind: str  # enum_case|protocol_requirement|declaration
    path: str
    line: int
    type_name: str
    name: str
    access: str


@dataclass
class ParsedFile:
    path: str
    decls: list[RawDecl]
    frames: list[TypeFrame]
    preview_spans: list[tuple[int, int]]
    bare_index: dict[str, list[int]]
    dot_index: dict[str, list[tuple[int, bool]]]


def parse_file(path: str, text: str) -> ParsedFile:
    stripped = strip_comments(text)
    lines = stripped.split("\n")
    depth_lines = _blank_strings(stripped).split("\n")

    frames: list[TypeFrame] = []
    preview_spans: list[tuple[int, int]] = []
    bare_index: dict[str, list[int]] = {}
    dot_index: dict[str, list[tuple[int, bool]]] = {}

    depth = 0
    stack: list[TypeFrame] = []
    body_depths: list[int] = []
    pending: TypeFrame | None = None

    for lineno, (raw, depth_raw) in enumerate(zip(lines, depth_lines, strict=True), start=1):
        m = _TYPE_RE.match(raw)
        if m:
            conformances = _parse_conformances(m.group("rest"))
            pending = TypeFrame(
                file=path,
                kind=m.group("kind"),
                name=m.group("name"),
                access=_access_of(m.group("mods")),
                conformances=conformances,
                is_preview="PreviewProvider" in conformances,
                start_line=lineno,
            )
        elif _PREVIEW_RE.match(raw):
            pending = TypeFrame(
                file=path,
                kind="preview",
                name="",
                access="internal",
                conformances=set(),
                is_preview=True,
                start_line=lineno,
            )

        in_preview = any(f.is_preview for f in stack)
        if stack and depth == body_depths[-1] and not in_preview:
            top = stack[-1]
            if top.kind == "enum":
                cm = _CASE_RE.match(raw)
                if cm:
                    for entry in _split_top_level_commas(cm.group("body")):
                        em = _CASE_ENTRY_RE.match(entry.strip())
                        if em:
                            top.cases.append(MemberSig(lineno, em.group("name")))
            # An enum is ALSO a type body for var/let/func/static members --
            # a namespace-style enum with no cases at all (`TransitionTiming`,
            # only `public static let`s) is a real, common shape, not an edge
            # case. Falls through from the `if` above rather than `elif` so
            # an enum gets both checks on the same line.
            if top.kind in ("protocol", "struct", "class", "actor", "extension", "enum"):
                fm = _MEMBER_FUNC_RE.match(raw)
                mm = fm or _MEMBER_VAR_RE.match(raw)
                if mm and not _has_excluded_attr(mm.group("mods")):
                    top.members.append(
                        MemberSig(lineno, mm.group("name"), _access_of(mm.group("mods")))
                    )

        for im in _IDENT_RE.finditer(raw):
            word = im.group(0)
            bare_index.setdefault(word, []).append(lineno)
            if im.start() > 0 and raw[im.start() - 1] == ".":
                is_pattern = _is_pattern_position(raw, im.start() - 1, im.end())
                dot_index.setdefault(word, []).append((lineno, is_pattern))

        for ch in depth_raw:
            if ch == "{":
                depth += 1
                if pending is not None:
                    stack.append(pending)
                    body_depths.append(depth)
                    pending = None
            elif ch == "}":
                depth -= 1
                if stack and depth < body_depths[-1]:
                    finished = stack.pop()
                    body_depths.pop()
                    finished.end_line = lineno
                    if finished.kind == "preview":
                        preview_spans.append((finished.start_line, lineno))
                    else:
                        frames.append(finished)

    while stack:
        finished = stack.pop()
        body_depths.pop()
        finished.end_line = len(lines)
        if finished.kind == "preview":
            preview_spans.append((finished.start_line, len(lines)))
        else:
            frames.append(finished)

    decls: list[RawDecl] = []
    for frame in frames:
        if frame.is_preview:
            continue
        if frame.kind == "enum":
            decls.extend(
                RawDecl("enum_case", path, c.line, frame.name, c.name, frame.access)
                for c in frame.cases
            )
            decls.extend(
                RawDecl("declaration", path, mm.line, frame.name, mm.name, mm.access)
                for mm in frame.members
            )
        elif frame.kind == "protocol":
            decls.extend(
                RawDecl("protocol_requirement", path, mm.line, frame.name, mm.name, frame.access)
                for mm in frame.members
            )
        elif frame.kind in ("struct", "class", "actor", "extension"):
            decls.extend(
                RawDecl("declaration", path, mm.line, frame.name, mm.name, mm.access)
                for mm in frame.members
            )

    return ParsedFile(path, decls, frames, preview_spans, bare_index, dot_index)


@dataclass
class Corpus:
    parsed: dict[str, ParsedFile]
    bare_index: dict[str, list[tuple[str, int]]]
    dot_index: dict[str, list[tuple[str, int, bool]]]
    frames: list[TypeFrame]
    preview_spans: dict[str, list[tuple[int, int]]]


def build_corpus(files: dict[str, str]) -> Corpus:
    parsed = {path: parse_file(path, text) for path, text in files.items()}
    bare_index: dict[str, list[tuple[str, int]]] = {}
    dot_index: dict[str, list[tuple[str, int, bool]]] = {}
    frames: list[TypeFrame] = []
    preview_spans: dict[str, list[tuple[int, int]]] = {}
    for path, pf in parsed.items():
        for name, lns in pf.bare_index.items():
            bare_index.setdefault(name, []).extend((path, ln) for ln in lns)
        for name, entries in pf.dot_index.items():
            dot_index.setdefault(name, []).extend((path, ln, pat) for (ln, pat) in entries)
        frames.extend(pf.frames)
        if pf.preview_spans:
            preview_spans[path] = pf.preview_spans
    return Corpus(parsed, bare_index, dot_index, frames, preview_spans)


def _protocol_impl_exclusions(
    protocol_name: str, req_name: str, frames: list[TypeFrame]
) -> set[tuple[str, int]]:
    out: set[tuple[str, int]] = set()
    for f in frames:
        if f.kind in ("struct", "class", "actor", "enum") and protocol_name in f.conformances:
            out.update((f.file, m.line) for m in f.members if m.name == req_name)
    return out


def _in_span(path: str, line: int, spans: dict[str, list[tuple[int, int]]]) -> bool:
    return any(s <= line <= e for (s, e) in spans.get(path, []))


def count_references(decl: RawDecl, corpus: Corpus, test_files: set[str]) -> tuple[int, int, int]:
    """(references_production, references_in_tests, references_in_previews)."""
    excluded: dict[tuple[str, int], int] = {(decl.path, decl.line): 1}
    if decl.kind == "protocol_requirement":
        for key in _protocol_impl_exclusions(decl.type_name, decl.name, corpus.frames):
            excluded[key] = excluded.get(key, 0) + 1

    scope = {decl.path} if decl.access in ("private", "fileprivate") else None

    if decl.kind == "enum_case":
        entries = [(f, ln) for (f, ln, is_pat) in corpus.dot_index.get(decl.name, []) if not is_pat]
    else:
        entries = list(corpus.bare_index.get(decl.name, []))

    prod = test = preview = 0
    for f, ln in entries:
        if excluded.get((f, ln), 0) > 0:
            excluded[(f, ln)] -= 1
            continue
        if scope is not None and f not in scope:
            continue
        if f in test_files:
            test += 1
        elif _in_span(f, ln, corpus.preview_spans):
            preview += 1
        else:
            prod += 1
    return prod, test, preview
