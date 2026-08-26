# dual-registry-split — behavior note

`stored_field_names` now recognizes a Derived marker whether it was
imported from `markers_native` or from `markers_legacy` -- two independent
modules that each define their own `Derived` object, for record specs
written against either vocabulary. It also sees through a `Tagged[...]`
wrapper, and resolves a stringified annotation by evaluating it in the
record's own namespace, falling back to a source-text match only when that
evaluation fails.

One case still isn't recognized: a field locally aliased to a registry's
`Derived` object (`from markers_legacy import Derived as LocalDerived`)
whose annotation is *also* an unresolvable forward reference. When the
annotation resolves, the alias doesn't matter -- the evaluated object is
the same registered marker either way. But when resolution fails, only the
raw source text is available, and the fallback match only knows the literal
spelling `Derived[`, not whatever alias a given caller chose. Closing that
in general would mean either evaluating an annotation that can't be
evaluated, or teaching the fallback every alias a caller might pick.
