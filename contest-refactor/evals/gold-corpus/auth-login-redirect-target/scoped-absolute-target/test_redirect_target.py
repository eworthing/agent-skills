#!/usr/bin/env python3
"""redirect_target's own bundled test suite (this variant).

Run directly: python3 test_redirect_target.py -- exits 0 on success.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gate import require_sign_in
from redirect_target import redirect_target_for
from request import Request


def test_hostless_entry_gets_a_relative_target_with_query() -> None:
    request = Request(scheme="https", host="app.example", path="/private/report", query="year=2026")
    target = redirect_target_for(request, "/sign-in/")
    assert target == "/private/report?year=2026", target


def test_same_host_entry_gets_a_relative_target() -> None:
    request = Request(scheme="https", host="app.example", path="/private/report")
    target = redirect_target_for(request, "https://app.example/sign-in/")
    assert target == "/private/report", target


def test_cross_host_entry_gets_the_full_absolute_target() -> None:
    request = Request(scheme="https", host="app.example", path="/private/report", query="year=2026")
    target = redirect_target_for(request, "https://accounts.other.example/sign-in/")
    assert target == "https://app.example/private/report?year=2026", target


def test_gated_view_redirects_when_signed_out() -> None:
    @require_sign_in()
    def view(request):
        return "view ran"

    request = Request(scheme="https", host="app.example", path="/private/report")
    result = view(request)
    assert result.startswith("/sign-in/?next="), result


def test_gated_view_runs_when_signed_in() -> None:
    @require_sign_in()
    def view(request):
        return "view ran"

    request = Request(scheme="https", host="app.example", path="/private/report")
    request.principal = "alice"
    assert view(request) == "view ran"


def main() -> int:
    test_hostless_entry_gets_a_relative_target_with_query()
    test_same_host_entry_gets_a_relative_target()
    test_cross_host_entry_gets_the_full_absolute_target()
    test_gated_view_redirects_when_signed_out()
    test_gated_view_runs_when_signed_in()
    print("OK: test_redirect_target.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
