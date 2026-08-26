# scoped-absolute-target — behavior note

A gated view's sign-in redirect now carries the request's full absolute
URL as its return target by default, including the query string. When the
sign-in endpoint is served from the same scheme and host as the request --
or declares no scheme/host of its own, which covers a same-service,
path-only sign-in endpoint -- the return target is downgraded to a bare
relative path (still with its query string) instead, since a fully
qualified URL adds nothing there and only exposes the calling host in the
sign-in endpoint's own URL.
