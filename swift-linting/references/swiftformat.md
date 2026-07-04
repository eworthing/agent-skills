# SwiftFormat Reference

SwiftFormat owns **how code looks**: layout, whitespace, wrapping, punctuation. Config: `.swiftformat`.

## Vertical Formatting

```swift
// LLM-friendly: each parameter on its own line
func configure(
    title: String,
    subtitle: String,
    isEnabled: Bool,
) {
    // ...
}

// Avoid: harder to diff, easy to miss changes
func configure(title: String, subtitle: String, isEnabled: Bool) {
```

Benefits:
- One parameter per line → cleaner git diffs
- LLMs add/remove parameters without reformatting entire signature
- Easier to spot missing or extra parameters in review

## Trailing Commas

The `trailingCommas` rule (default `always`) adds a trailing comma to wrapped
collection literals, function arguments, and tuples — one element per line.

```swift
// Adding a new element changes only one line
let states: [State] = [
    .loading,
    .success,
    .error,  // trailing comma
]
```

Benefits:
- Reduces diff noise when appending items
- Prevents the common LLM mistake of forgetting commas

Enum cases are the exception: the separate `wrapEnumCases` rule puts each `case`
on its own line with **no** trailing comma (`case loading` / `case success`) —
not a comma-chained list.

## Explicit Self

- `--self init-only` removes redundant `self.` in most contexts
- Keeps `self.` in initializers where it disambiguates
- **Exception:** Swift 6 requires explicit `self.` in `@autoclosure` contexts (see below)

## Swift 6 Logger `@autoclosure` Gotcha

Swift 6 strict concurrency requires explicit `self.` when capturing properties in `@autoclosure` contexts. This conflicts with SwiftFormat's `redundantSelf` rule.

```swift
// BUILD ERROR: Swift 6 strict concurrency
Logger.app.debug("Count: \(items.count)")  // 'items' needs 'self.'

// CORRECT: explicit self required
// swiftformat:disable redundantSelf
Logger.app.debug("Count: \(self.items.count)")
// swiftformat:enable redundantSelf
```

Disable comment placement:
- Single-line: `// swiftformat:disable:next redundantSelf`
- Multi-line: block disable/enable pair

## Code Organization (MARK Sections)

SwiftFormat auto-generates `// MARK: -` sections:
- Lifecycle, Internal, Private visibility groups
- Only triggers on types past the configured line thresholds — read `.swiftformat`
  for this repo's values (typical: struct 40 / class 50 / enum 30)

## Running SwiftFormat

```bash
# Check what would change (no modifications)
swiftformat . --lint

# Apply formatting
swiftformat .

# Format specific file
swiftformat Sources/State/AppState.swift
```
