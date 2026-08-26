"""The return-target a gated view's sign-in redirect carries, so a
principal lands back where they started after signing in.

Defaults to the request's own absolute URL. If the sign-in endpoint is
served from the same scheme and host as the request -- or declares no
scheme/host of its own -- a bare path (with its query string) is enough,
and avoids embedding the calling host into the sign-in endpoint's own URL
for no reason.
"""

from __future__ import annotations

from urllib.parse import urlsplit


def redirect_target_for(request, entry_url: str) -> str:
    absolute = request.current_absolute_url()
    entry_scheme, entry_netloc = urlsplit(entry_url)[:2]
    current_scheme, current_netloc = urlsplit(absolute)[:2]
    if (not entry_scheme or entry_scheme == current_scheme) and (
        not entry_netloc or entry_netloc == current_netloc
    ):
        return request.current_path_and_query()
    return absolute
