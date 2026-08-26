"""A decorator that gates a view behind sign-in, redirecting an
unauthenticated request to the sign-in endpoint with a return target
attached.
"""

from __future__ import annotations

import functools
from collections.abc import Callable

from redirect_target import redirect_target_for

DEFAULT_ENTRY_URL = "/sign-in/"
DEFAULT_RETURN_PARAM_NAME = "next"


def require_sign_in(entry_url: str | None = None, return_param_name: str | None = None):
    """Wrap `view` so it runs only for a request with a signed-in
    `.principal`; otherwise it returns a redirect to the sign-in endpoint
    carrying a return target."""

    def decorator(view: Callable) -> Callable:
        @functools.wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.principal is None:
                target_entry_url = entry_url or DEFAULT_ENTRY_URL
                target_param = return_param_name or DEFAULT_RETURN_PARAM_NAME
                target = redirect_target_for(request, target_entry_url)
                return f"{target_entry_url}?{target_param}={target}"
            return view(request, *args, **kwargs)

        return wrapper

    return decorator
