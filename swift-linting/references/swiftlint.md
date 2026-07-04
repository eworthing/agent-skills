# SwiftLint Reference

SwiftLint owns **what code does**: semantics, safety, correctness, complexity. Config: `.swiftlint.yml`.

## Running SwiftLint

```bash
# Warnings + errors
swiftlint lint

# Errors only
swiftlint lint --quiet

# Auto-fix what can be fixed
swiftlint lint --fix

# Deeper analysis (slower, catches unused code)
swiftlint analyze
```

## Pre-commit Verification

```bash
swiftformat . --lint && swiftlint lint --quiet
```

## Rule Categories

### Safety (opt-in, prevent crashes)
- `force_unwrapping`, `force_cast`, `force_try`
- `unhandled_throwing_task`, `weak_delegate`, `unowned_variable_capture`

Concurrency-semantic lints (`async_without_await`, `unowned_variable_capture`,
`weak_delegate`, `unhandled_throwing_task`) are owned authoritatively by the
`swift-concurrency` skill's `references/linting.md` — the list above is orientation
only; go there for the diagnose-and-fix workflow.

### Accessibility (opt-in)
- `accessibility_label_for_image`
- `accessibility_trait_for_button`

### Performance (opt-in)
- `empty_count`, `first_where`, `contains_over_filter_count`
- `reduce_into`

## File Length Rule

`file_length` enforces the repo's configured cap — read `.swiftlint.yml` for the value (typical: 600 lines, 400 for overlays). When triggered, do not silence — split the file. See the `swift-file-splitting` skill for the refactor workflow.

## Disable Comments

See [disable-comments.md](disable-comments.md) for `:next` vs `:this` directives and common placement mistakes.
