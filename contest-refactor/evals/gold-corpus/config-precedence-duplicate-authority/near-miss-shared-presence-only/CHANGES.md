# Changes

Layer presence now goes through one helper, `_carries`, instead of each
function spelling out its own membership test. Both `effective_value` and
`describe_source` call it, so "does this layer carry the key" has a single
definition and an explicitly empty value counts as carried in both.

No change to the layer order or to which value any key resolves to.
