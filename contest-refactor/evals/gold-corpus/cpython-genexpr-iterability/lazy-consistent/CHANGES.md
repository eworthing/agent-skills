# lazy-consistent — behavior note

`LazySelect(source)` no longer validates `source` at construction time.

A `source` that is not iterable, or whose `__iter__()` returns an iterator
that lacks `__iter__` itself, now raises only once you actually iterate the
`LazySelect` -- not when you build it. This matches every other lazy
pipeline in this module and restores support for the second case, which
worked before the eager guard was added.

`test_lazyselect.py`'s `test_immediate_iterability_check` is replaced by
`test_iterability_check_is_lazy`, which asserts the new (correct) timing
instead of the old one.
