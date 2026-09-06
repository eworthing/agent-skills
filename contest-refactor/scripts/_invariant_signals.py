#!/usr/bin/env python3
"""_invariant_signals.py — Queue D (invariant) candidate-evidence analyzer.

Pure analyzer for hotspot-scanner Queue D, added by
OCR-GAP-REMEDIATION-PLAN-2026-09-03 W1a. Stdlib-only; imports nothing from the
scanner family (audit_hotspots.py, _ast_grep.py, _fs_filters.py). It receives
Swift source spans as text and returns candidate evidence -- the caller owns
ast-grep invocation and file discovery.

Five signals, each a mechanical proxy for a value-type invariant gap (a
one-sided range guard, an unchecked clamp, a duplicate-ID collection, a
`Codable` conformance that bypasses a throwing init, an unbounded `Int(Double)`
conversion). All predicates are name-local and lexical -- regex over masked-ish
Swift text, not a real parse. That is a documented limit (an aliased floating
type such as `typealias Seconds = Double` is invisible here), not a bug: the
Critic re-derives every candidate from source semantics before it becomes a
finding (promotion_allowed: false upstream).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

FLOATING_TYPES = ("Double", "Float", "TimeInterval", "CGFloat")

_TYPE_HEADER_RE = re.compile(r"\b(?:class|struct|actor|enum)\s+([A-Za-z_]\w*)")
_CONFORMANCE_RE = re.compile(r"\b(?:class|struct|actor|enum)\s+\w+(?:<[^>]*>)?\s*:\s*([^{]+)")
_INIT_FROM_RE = re.compile(r"\binit\s*\(\s*from\b")
_INIT_OPEN_RE = re.compile(r"\binit\s*\(")
_THROWS_TAIL_RE = re.compile(r"\s*(?:async\s+)?throws\b")
# ponytail: catches any `var|let name: Double` line anywhere in the type span,
# including inside a member body that happens to match the same shape (a local
# with the same declaration form). Over-collecting a local as a "stored
# property" only widens clamp_unchecked's name union, never narrows it, and
# the Critic re-derives from source -- upgrade to a real parse if that proves
# to matter on a live corpus.
_STORED_FLOATING_RE = re.compile(
    r"\b(?:var|let)\s+(\w+)\s*:\s*(?:" + "|".join(FLOATING_TYPES) + r")\b"
)
_FLOATING_PARAM_RE = re.compile(r"\b(\w+)\s*:\s*(?:" + "|".join(FLOATING_TYPES) + r")\b")
_ID_ARRAY_PARAM_RE = re.compile(r"\b(\w+)\s*:\s*\[\s*[A-Za-z_]\w*ID\s*\]")
_ARRAY_PARAM_RE = re.compile(r"\b(\w+)\s*:\s*\[\s*[A-Za-z_]\w*\s*\]")
_FUNC_NAME_RE = re.compile(r"\bfunc\s+(\w+)")
_MIN_MAX_CALL_RE = re.compile(r"\b(?:min|max)\s*\(")
_MIN_CALL_RE = re.compile(r"\bmin\s*\(")
_ALLSATISFY_CALL_RE = re.compile(r"\b(\w+)\.allSatisfy\s*\(")
_FOR_LOOP_RE = re.compile(r"\bfor\s+(\w+)\s+in\s+(\w+)\s*\{")
_CLOSURE_NAMED_PARAM_RE = re.compile(r"^\s*\{\s*(\w+)\s+in\b")
# NaN-admit/reject form classification (rule 1): which of these keywords sits
# closest before a comparison decides whether NaN can survive it. A direct
# comparison inside one of these REJECTS NaN (any comparison against NaN is
# false, so the guard/allSatisfy/precondition fails and the value is
# rejected). An `if`-triggered throw does the opposite: the throw condition
# is also false for NaN, so the throw never fires and NaN is ADMITTED.
_KEYPATH_FINITE_RE = re.compile(r"\\\.isFinite\b")
_GUARD_FORM_KEYWORDS = ("guard", "allSatisfy(", "precondition(")
_FORM_KEYWORDS = (*_GUARD_FORM_KEYWORDS, "if ")


@dataclass
class InvariantSignals:
    one_sided_guard: int = 0
    clamp_unchecked: int = 0
    id_collection_no_uniqueness: int = 0
    codable_bypasses_throwing_init: int = 0
    int_conversion_unbounded: int = 0


@dataclass
class InvariantCandidate:
    path: str
    symbol: str
    start_line: int
    end_line: int
    signals: InvariantSignals


@dataclass
class TypeContext:
    type_name: str
    stored_floating_properties: set[str] = field(default_factory=set)
    conformances: set[str] = field(default_factory=set)
    has_init_from: bool = False
    has_throwing_init: bool = False


def _balanced_content(text: str, open_idx: int, open_char: str = "(", close_char: str = ")") -> str:
    """Text strictly between the bracket at `open_idx` and its match."""
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == open_char:
            depth += 1
        elif text[i] == close_char:
            depth -= 1
            if depth == 0:
                return text[open_idx + 1 : i]
    return text[open_idx + 1 :]


def _param_list_text(header: str) -> str:
    open_idx = header.find("(")
    if open_idx == -1:
        return ""
    return _balanced_content(header, open_idx)


def _floating_names(param_list_text: str) -> set[str]:
    return set(_FLOATING_PARAM_RE.findall(param_list_text))


def _has_throwing_init(text: str) -> bool:
    """`init(...)  throws` / `init(...) async throws`, with the param list
    balanced-paren scanned so a closure-typed param (`(Int) -> Void`) can't
    truncate the match early like a `[^)]*` regex would."""
    for m in _INIT_OPEN_RE.finditer(text):
        open_idx = m.end() - 1
        params = _balanced_content(text, open_idx)
        after = text[open_idx + 1 + len(params) + 1 :]
        if _THROWS_TAIL_RE.match(after):
            return True
    return False


def analyze_type(path: str, type_span: str, type_lines: tuple[int, int]) -> TypeContext:
    del path, type_lines  # identity carried by the caller; not needed here
    header = type_span.split("{", 1)[0]
    type_match = _TYPE_HEADER_RE.search(header)
    type_name = type_match.group(1) if type_match else ""

    conformances: set[str] = set()
    conf_match = _CONFORMANCE_RE.search(header)
    if conf_match:
        clause = conf_match.group(1).split(" where ")[0]
        conformances = {
            part.strip().removeprefix("any ").strip()
            for part in re.split(r"[,&]", clause)
            if part.strip()
        }

    return TypeContext(
        type_name=type_name,
        stored_floating_properties=set(_STORED_FLOATING_RE.findall(type_span)),
        conformances=conformances,
        has_init_from=bool(_INIT_FROM_RE.search(type_span)),
        has_throwing_init=_has_throwing_init(type_span),
    )


def _has_finite_or_nan_guard(span: str, name: str) -> bool:
    # No longer a blanket "allSatisfy is nearby" suppression: that predated
    # rule 1/3's guard-form + collection-element-field handling and directly
    # contradicted it -- allSatisfy is exactly where those comparisons live.
    # isFinite/isNaN stay as explicit, name-scoped suppressions.
    escaped = re.escape(name)
    if re.search(rf"\b{escaped}\.isFinite\b", span):
        return True
    if re.search(rf"\b{escaped}\.isNaN\b", span):
        return True
    # Keypath idiom: `[d.a, d.b].allSatisfy(\.isFinite)`, or a closure that
    # applies it and is later handed to `allSatisfy(isFinite)`. Lexically: the
    # field name appears in the 400 chars before a `\.isFinite` keypath -- the
    # same lookback window `_nearest_form_keyword` uses.
    for m in _KEYPATH_FINITE_RE.finditer(span):
        if re.search(rf"\b{escaped}\b", span[max(0, m.start() - 400) : m.start()]):
            return True
    return False


def _nearest_form_keyword(span: str, pos: int) -> str | None:
    """Which of guard/allSatisfy(/precondition(/if sits closest before `pos`.

    ponytail: a 400-char lookback window, not a real statement-boundary
    parse. Good enough for the single-line guard/if shapes these rules
    target; widen (or parse braces properly) if a live corpus needs more.
    """
    window = span[max(0, pos - 400) : pos]
    best_kw, best_idx = None, -1
    for kw in _FORM_KEYWORDS:
        idx = window.rfind(kw)
        if idx > best_idx:
            best_idx, best_kw = idx, kw
    return best_kw


def _rejects_nan(span: str, pos: int) -> bool:
    """True when the comparison at `pos` sits in a guard-style form whose
    direct-comparison success condition is false for NaN (so NaN cannot
    proceed) -- as opposed to an `if cond { throw }` form, whose FAILURE
    condition is also false for NaN, letting NaN silently survive."""
    return _nearest_form_keyword(span, pos) in _GUARD_FORM_KEYWORDS


def _comparison_occurrences(span: str, name: str) -> list[tuple[str, int]]:
    """(direction, match_start) for every `name`-naming comparison, direction
    normalized so `X < name` reads as `name > X` ("gt") and vice versa."""
    escaped = re.escape(name)
    occurrences: list[tuple[str, int]] = []
    for m in re.finditer(rf"\b{escaped}\b\s*(>=|<=|>|<)", span):
        occurrences.append(("gt" if m.group(1) in (">", ">=") else "lt", m.start()))
    # Right operand may carry a receiver (`>= $0.startSeconds`, `< elem.end`);
    # `$` is not a word char, so the optional `[\w$]+\.` prefix is explicit.
    for m in re.finditer(rf"(>=|<=|>|<)\s*(?:[\w$]+\.)?\b{escaped}\b", span):
        occurrences.append(("lt" if m.group(1) in (">", ">=") else "gt", m.start()))
    return occurrences


def _min_clamp_positions(span: str, name: str) -> list[int]:
    """Start positions of every `min(` call (an upper-bound clamp) whose
    argument list names `name`."""
    escaped = re.escape(name)
    return [
        m.start()
        for m in _MIN_CALL_RE.finditer(span)
        if re.search(rf"\b{escaped}\b", _balanced_content(span, m.end() - 1))
    ]


def _count_one_sided_guard(span: str, names: set[str], finite_scope: str | None = None) -> int:
    """`finite_scope` is where isFinite/isNaN checks are looked up (defaults to
    `span`); collection-element regions pass the whole member, because the
    finite guard for a field usually sits in a different `allSatisfy` than the
    bound checks (post-fix PlaybackSpec.init)."""
    count = 0
    for name in names:
        occurrences = _comparison_occurrences(span, name)
        directions = {d for d, _ in occurrences}
        if len(directions) != 1 or _has_finite_or_nan_guard(finite_scope or span, name):
            continue
        (direction,) = directions
        if direction == "gt" and all(_rejects_nan(span, pos) for _, pos in occurrences):
            # Lower-bound-only in guard form (`guard x >= 0`): NaN fails the
            # comparison and is rejected, negatives are rejected; only +inf
            # survives. That is the canonical Swift validation idiom, not a
            # gap the rule should flag. The negated form (`if x < 0 { throw }`)
            # admits NaN and still fires.
            continue
        count += len(occurrences)
    return count


def _count_clamp_unchecked(span: str, names: set[str]) -> int:
    count = 0
    for name in names:
        escaped = re.escape(name)
        clamp_pos = None
        for m in _MIN_MAX_CALL_RE.finditer(span):
            content = _balanced_content(span, m.end() - 1)
            if re.search(rf"\b{escaped}\b", content):
                clamp_pos = m.start()
                break
        if clamp_pos is None or re.search(rf"\b{escaped}\.isFinite\b", span):
            continue
        # A guard-form lower-bound check for `name` earlier in the span
        # already rejects NaN before this clamp runs -- fid 131's shape.
        guarded_before = any(
            d == "gt" and pos < clamp_pos and _rejects_nan(span, pos)
            for d, pos in _comparison_occurrences(span, name)
        )
        if guarded_before:
            continue
        count += 1
    return count


def _closure_bound_name(closure_text: str) -> str:
    m = _CLOSURE_NAMED_PARAM_RE.match(closure_text.strip())
    return m.group(1) if m else "$0"


def _collection_element_scan_regions(span: str, param_list_text: str) -> list[tuple[str, set[str]]]:
    """(container_text, field_names) pairs for `arrayParam.allSatisfy {
    $0.field ... }` (or a named closure param, `{ elem in ... elem.field
    ... }`) and `for elem in arrayParam { ... }` over an array-typed
    PARAMETER. Each pair is scanned for one_sided_guard on its OWN text,
    not the whole member span: a same-named comparison sitting elsewhere in
    the member (Tiercade's `.sorted { $0.index < $1.index }` textually after
    an unrelated `for tier in tiers` loop that also reads `tier.index`) must
    never leak into a field's comparison count. A field that never appears
    in a comparison inside its own container simply contributes nothing --
    no separate "compared against a floating-looking bound" filter needed."""
    array_params = set(_ARRAY_PARAM_RE.findall(param_list_text))
    if not array_params:
        return []

    # One combined region per array parameter: bounds for one field are often
    # split across several `allSatisfy` guards (`>= 0` in one, `<= half` in
    # the next), and the direction union must see all of them, while text
    # outside those containers (an unrelated `.sorted { $0.index < ... }`)
    # still stays out.
    texts: dict[str, list[str]] = {}
    fields_by_param: dict[str, set[str]] = {}
    for m in _ALLSATISFY_CALL_RE.finditer(span):
        param = m.group(1)
        if param not in array_params:
            continue
        content = _balanced_content(span, m.end() - 1)
        bound = re.escape(_closure_bound_name(content))
        # (?<![\w$]) not \b: the implicit closure param is "$0", and "$" is
        # not a word char, so `\b` never matches right before it.
        fields = set(re.findall(rf"(?<![\w$]){bound}\.(\w+)", content))
        if fields:
            # Keep the call keyword on the region text so `_rejects_nan` still
            # sees the guard form: an element failing an allSatisfy comparison
            # fails the enclosing guard, exactly like `guard x >= 0`.
            texts.setdefault(param, []).append("allSatisfy(" + content)
            fields_by_param.setdefault(param, set()).update(fields)

    for m in _FOR_LOOP_RE.finditer(span):
        elem, arr = m.group(1), m.group(2)
        if arr not in array_params:
            continue
        body = _balanced_content(span, m.end() - 1, open_char="{", close_char="}")
        fields = set(re.findall(rf"\b{re.escape(elem)}\.(\w+)\b", body))
        if fields:
            texts.setdefault(arr, []).append(body)
            fields_by_param.setdefault(arr, set()).update(fields)

    return [("\n".join(texts[p]), fields_by_param[p]) for p in texts]


def _count_id_collection_no_uniqueness(span: str, param_list_text: str) -> int:
    count = 0
    for name in _ID_ARRAY_PARAM_RE.findall(param_list_text):
        escaped = re.escape(name)
        if re.search(rf"Set\(\s*{escaped}\b", span):
            continue
        if re.search(rf"Dictionary\(grouping\s*:\s*{escaped}\b", span):
            continue
        if re.search(rf"\b{escaped}\b\.allSatisfy\s*\(", span):
            continue
        if not re.search(rf"self\.\w+\s*=\s*{escaped}\b", span):
            continue
        count += 1
    return count


def _count_int_conversion_unbounded(span: str, names: set[str]) -> int:
    count = 0
    for name in names:
        escaped = re.escape(name)
        # A local "chains" back to p if p appears anywhere on the line that
        # defines it -- loose on purpose, so a clamp/ternary expression
        # built around p (`let clamped = p.isFinite ? max(p, 0) : 0`) still
        # traces back to p, not just a bare `let clamped = p`.
        aliases = set(re.findall(rf"^\s*let\s+(\w+)\s*=.*\b{escaped}\b.*$", span, re.MULTILINE))
        chain = {name, *aliases}
        fires = any(re.search(rf"\bInt\(\s*{re.escape(c)}\s*\)", span) for c in chain)
        if not fires:
            continue
        # Fires when NOTHING in the name chain is ever upper-bounded by a
        # `min(` clamp -- a floor (`max(`) alone doesn't stop `Int(_:)`
        # trapping on a huge finite value, isFinite or not (fid 262's shape:
        # `let clamped = time.isFinite ? max(time, 0) : 0; Int(clamped)`).
        if any(_min_clamp_positions(span, c) for c in chain):
            continue
        count += 1
    return count


def analyze_member(
    path: str,
    ctx: TypeContext,
    member_kind: str,
    member_span: str,
    member_lines: tuple[int, int],
) -> InvariantCandidate | None:
    header = member_span.split("{", 1)[0]
    param_list_text = _param_list_text(header)
    floating_params = _floating_names(param_list_text)

    if member_kind == "init_declaration":
        name = "init"
        is_construction = True
    else:
        name_match = _FUNC_NAME_RE.search(header)
        name = name_match.group(1) if name_match else "unknown"
        # Per the plan's span table: one_sided_guard, clamp_unchecked and
        # id_collection_no_uniqueness are construction-time validation rules
        # -- restricting them to inits and validate*/make* functions is the
        # whole premise (an ordinary layout/color-math function comparing
        # CGFloats is not constructing a value type). int_conversion_unbounded
        # stays unscoped: a trap is not construction-specific.
        is_construction = name.startswith(("validate", "make"))

    if is_construction:
        one_sided_guard_count = _count_one_sided_guard(member_span, floating_params)
        for region_text, region_fields in _collection_element_scan_regions(
            member_span, param_list_text
        ):
            one_sided_guard_count += _count_one_sided_guard(
                region_text, region_fields, finite_scope=member_span
            )
        clamp_unchecked_count = _count_clamp_unchecked(
            member_span, floating_params | ctx.stored_floating_properties
        )
        id_collection_count = _count_id_collection_no_uniqueness(member_span, param_list_text)
    else:
        one_sided_guard_count = 0
        clamp_unchecked_count = 0
        id_collection_count = 0

    signals = InvariantSignals(
        one_sided_guard=one_sided_guard_count,
        clamp_unchecked=clamp_unchecked_count,
        id_collection_no_uniqueness=id_collection_count,
        int_conversion_unbounded=_count_int_conversion_unbounded(member_span, floating_params),
    )

    if not (
        signals.one_sided_guard
        or signals.clamp_unchecked
        or signals.id_collection_no_uniqueness
        or signals.int_conversion_unbounded
    ):
        return None

    symbol = f"{ctx.type_name}.{name}" if ctx.type_name else name

    return InvariantCandidate(
        path=path,
        symbol=symbol,
        start_line=member_lines[0],
        end_line=member_lines[1],
        signals=signals,
    )


def analyze_type_level(
    path: str, ctx: TypeContext, type_lines: tuple[int, int]
) -> InvariantCandidate | None:
    fires = (
        bool(ctx.conformances & {"Codable", "Decodable"})
        and ctx.has_throwing_init
        and not ctx.has_init_from
    )
    if not fires or not ctx.type_name:
        return None
    return InvariantCandidate(
        path=path,
        symbol=ctx.type_name,
        start_line=type_lines[0],
        end_line=type_lines[1],
        signals=InvariantSignals(codable_bypasses_throwing_init=1),
    )


def select_top_k(candidates: list[InvariantCandidate], top_k: int) -> list[InvariantCandidate]:
    """Rank by signal total desc, path asc, start_line asc; return the top `top_k`."""

    def _signal_total(candidate: InvariantCandidate) -> int:
        s = candidate.signals
        return (
            s.one_sided_guard
            + s.clamp_unchecked
            + s.id_collection_no_uniqueness
            + s.codable_bypasses_throwing_init
            + s.int_conversion_unbounded
        )

    ranked = sorted(candidates, key=lambda c: (-_signal_total(c), c.path, c.start_line))
    return ranked[:top_k]


def candidate_id(path: str, symbol: str, start_line: int, end_line: int) -> str:
    """First 12 lowercase hex chars of SHA-1 over `posix_path|symbol|start|end`."""
    posix_path = path.replace("\\", "/")
    raw = f"{posix_path}|{symbol}|{start_line}|{end_line}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
