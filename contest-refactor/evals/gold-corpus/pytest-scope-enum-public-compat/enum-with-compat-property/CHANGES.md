# enum-with-compat-property — behavior note

`Handle` used to carry a plain `span: str` attribute. It now carries
`_span: Span` (the new ordered enum) internally, with a read-only `span`
property that returns the string value for compatibility.

This one might cause some confusion: the internal attribute has a
different type than the public property of the same name. Every existing
caller that only ever read `.span` sees no change -- comparisons against a
plain string, use as a dict key, and string formatting all still work
exactly as before.
