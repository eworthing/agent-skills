"""Native marker vocabulary for this package's own record specs.

`Derived` marks a field as computed rather than stored: a record scanner
sees it on a field's annotation and leaves that name out of the record's
stored-field set.
"""

from __future__ import annotations


class _MarkerForm:
    """A subscriptable marker special form, e.g. `Derived` or `Derived[int]`."""

    def __init__(self, name: str) -> None:
        self._name = name

    def __getitem__(self, item: object) -> _MarkerAlias:
        return _MarkerAlias(self, item)

    def __repr__(self) -> str:
        return self._name


class _MarkerAlias:
    """The parametrized form, e.g. `Derived[int]`.

    `__origin__` points back at the bare marker, so a parametrized use is
    recognized the same way a bare one is.
    """

    def __init__(self, origin: _MarkerForm, item: object) -> None:
        self.__origin__ = origin
        self.__args__ = (item,)

    def __repr__(self) -> str:
        return f"{self.__origin__!r}[{self.__args__[0]!r}]"


Derived = _MarkerForm("Derived")
