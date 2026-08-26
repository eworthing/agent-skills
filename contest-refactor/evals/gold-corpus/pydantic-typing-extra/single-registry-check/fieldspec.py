"""Record-spec scanning: which annotated names are stored fields and which
are Derived markers that a record scanner should leave out of storage.

A field's annotation may arrive already evaluated, or as an unresolved
forward reference (a name that doesn't exist yet in the record's own
namespace) -- in the latter case, recognition falls back to matching the
annotation's raw source text against the one spelling this module knows:
a bare `Derived[...]`, optionally qualified by a module prefix.
"""

from __future__ import annotations

import re

import markers_native

_DERIVED_PATTERN = re.compile(r"(\w+\.)?Derived\[")


class _Unresolved:
    """An annotation that failed to evaluate in its record's namespace --
    stands in for a raw forward-reference string."""

    def __init__(self, source: str) -> None:
        self.source = source

    def __repr__(self) -> str:
        return f"_Unresolved({self.source!r})"


def _is_native_derived(obj: object) -> bool:
    return obj is not None and obj is markers_native.Derived


def is_derived(tp: object) -> bool:
    """Whether `tp` -- resolved or not -- marks a record field as Derived."""
    if _is_native_derived(tp):
        return True
    if _is_native_derived(getattr(tp, "__origin__", None)):
        return True
    return isinstance(tp, _Unresolved) and bool(_DERIVED_PATTERN.match(tp.source))


def _resolve(source: str, namespace: dict[str, object]) -> object:
    # A record's raw annotation source, evaluated in the record's own
    # namespace; a name that doesn't exist there yet becomes _Unresolved
    # rather than raising all the way out.
    try:
        return eval(source, namespace)
    except NameError:
        return _Unresolved(source)


def stored_field_names(annotations: dict[str, str], namespace: dict[str, object]) -> list[str]:
    """The names from `annotations` that belong in a record's stored-field
    set -- everything except a name annotated as Derived."""
    stored = []
    for name, source in annotations.items():
        tp = _resolve(source, namespace)
        if not is_derived(tp):
            stored.append(name)
    return stored
