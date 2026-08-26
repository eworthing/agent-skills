"""Reads the entry-endpoint metadata require_sign_in staples onto a gated
view, without re-parsing decorator arguments. A separate module from
gate.py because it runs at a different time -- a startup-time scan over
every gated view, not at request time.
"""

from __future__ import annotations


def entry_endpoint_for(view) -> str | None:
    return getattr(view, "entry_url", None)


def return_param_name_for(view) -> str | None:
    return getattr(view, "return_param_name", None)
