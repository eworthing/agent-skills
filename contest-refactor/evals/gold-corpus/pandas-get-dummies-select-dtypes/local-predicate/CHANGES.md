# local-predicate — behavior note

`encode_categoricals` no longer calls `column_subset` with a fixed list of
type aliases. It now expresses the columns it wants directly with
`should_encode`.

Pure refactor: `should_encode` unwraps a `Packed` kind to its primitive the
same way `column_subset` does, so every column kind that used to be picked
up by the alias-list call is still picked up here, and nothing else is. No
change in which columns get encoded.
