"""A minimal stand-in for an inbound request: the scheme/host/path/query it
actually arrived on, plus whatever the client separately claims about its
own forwarding host (a raw, unvalidated value -- not the request's real
origin unless something in front of it validates that claim first).
"""

from __future__ import annotations


class Request:
    def __init__(
        self,
        scheme: str,
        host: str,
        path: str,
        query: str = "",
        forwarded_host: str | None = None,
    ) -> None:
        self.scheme = scheme
        self.host = host
        self.path = path
        self.query = query
        self.forwarded_host = forwarded_host
        self.principal = None

    def current_absolute_url(self) -> str:
        base = f"{self.scheme}://{self.host}{self.path}"
        return f"{base}?{self.query}" if self.query else base

    def current_path_and_query(self) -> str:
        return f"{self.path}?{self.query}" if self.query else self.path
