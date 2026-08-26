"""The return-target a gated view's sign-in redirect carries, so a
principal lands back where they started after signing in.
"""

from __future__ import annotations


def redirect_target_for(request, entry_url: str) -> str:
    return request.current_path_and_query()
