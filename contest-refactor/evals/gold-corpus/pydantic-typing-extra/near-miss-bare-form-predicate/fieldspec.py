"""Record-spec scanning: which annotated names are stored fields and which
are Derived markers that a record scanner should leave out of storage.

A field's Derived marker may come from either `markers_native` or
`markers_legacy` -- two independent modules that each define their own
`Derived` object, kept separate for record specs written against either
vocabulary. It may also be wrapped in `Tagged[...]` for extra metadata, and
its annotation may arrive as an unresolved forward reference (a name that
doesn't exist yet in the record's own namespace) rather than as an
already-evaluated object.
"""

from __future__ import annotations

import re
from functools import cache

import markers_legacy
import markers_native
from tags import _TaggedAlias

_MARKER_MODULES = (markers_native, markers_legacy)

_DERIVED_PATTERN = re.compile(r"((\w+\.)?Tagged\[)?(\w+\.)?Derived\[")


class _Unresolved:
    """An annotation that failed to evaluate in its record's namespace --
    stands in for a raw forward-reference string."""

    def __init__(self, source: str) -> None:
        self.source = source

    def __repr__(self) -> str:
        return f"_Unresolved({self.source!r})"


@cache
def _get_markers_named(name: str) -> tuple[object, ...]:
    """The `name` marker as defined in every registry module that has one."""
    result = tuple(getattr(module, name) for module in _MARKER_MODULES if hasattr(module, name))
    if not result:
        raise ValueError(f"no registry defines a marker named {name!r}")
    return result


def _is_registered_marker(obj: object, name: str) -> bool:
    return any(obj is candidate for candidate in _get_markers_named(name))


def is_derived_marker(tp: object) -> bool:
    """Whether `tp` is itself the Derived special form, bare or
    parametrized, from either registry.

    Note: in most cases you want `is_derived_annotation` instead -- this
    function does not see through a `Tagged[...]` wrapper and does not
    resolve an unresolved forward reference.
    """
    if _is_registered_marker(tp, "Derived"):
        return True
    return _is_registered_marker(getattr(tp, "__origin__", None), "Derived")


def is_derived_annotation(tp: object) -> bool:
    """Whether a record field annotated with `tp` should be treated as a
    Derived marker rather than a stored field.

    Unwraps a `Tagged[...]` wrapper and falls back to matching the raw
    source text when `tp` is an unresolved forward reference.
    """
    if isinstance(tp, _TaggedAlias):
        tp = tp.__tagged_type__
    if is_derived_marker(tp):
        return True
    return isinstance(tp, _Unresolved) and bool(_DERIVED_PATTERN.match(tp.source))


def _resolve(source: str, namespace: dict[str, object]) -> object:
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
        if not is_derived_marker(tp):
            stored.append(name)
    return stored
