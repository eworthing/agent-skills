# per-type-callables — behavior note

Type selection now turns each requested (or excluded) type name into its own
predicate callable, instead of matching every column against one shared
frozenset-membership test. A column is kept if any of the requested-type
predicates accepts it.

This localizes each type's matching rule as its own small function, ahead of
an upcoming change to how individual column types get matched. No
user-visible change: `select()` returns exactly the same columns as before
for every include/exclude combination.
