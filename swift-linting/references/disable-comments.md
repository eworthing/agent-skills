# SwiftLint Disable Comment Placement

SwiftLint's `:next` directive applies to the **immediately following line only**. Attributes and doc comments between the disable and the target silently break the suppression.

## `:next` vs `:this` Directives

| Directive | Applies To | Use When |
|-----------|-----------|----------|
| `disable:next` | Next line only | Nothing between comment and target |
| `disable:this` | Current line | Inline with target code |

## Common Mistake: Disable Before Attributes

```swift
// WRONG - :next applies to @ViewBuilder, not the function
// swiftlint:disable:next function_body_length
@ViewBuilder
func applyModals(app: AppState) -> some View { ... }
// Result: Warning still fires + "superfluous_disable_command" warning

// CORRECT - :this on the function line itself
@ViewBuilder
func applyModals(app: AppState) -> some View { // swiftlint:disable:this function_body_length
    ...
}
```

## Common Mistake: Disable Before Doc Comments

```swift
// WRONG - :next applies to doc comment, not function
// swiftlint:disable:next function_body_length
/// Commits staged candidates as new items.
func commitDroppedItemCandidates() async { ... }
// Result: Warning still fires + "orphaned_doc_comment" warning

// CORRECT - :this inline with function
/// Commits staged candidates as new items.
func commitDroppedItemCandidates() async { // swiftlint:disable:this function_body_length
    ...
}
```

## Diagnostic Warnings That Indicate Broken Disables

| Warning | Meaning |
|---------|---------|
| `superfluous_disable_command` | Disable isn't suppressing anything (wrong target line) |
| `orphaned_doc_comment` | Doc comment separated from its declaration by disable comment |

**If you see either after adding a disable, placement is wrong.**

## Quick Reference

```swift
// For function_body_length, line_length, large_tuple:
func foo() { // swiftlint:disable:this function_body_length

// For multi-line disables (rare):
// swiftlint:disable line_length
let longString = "..."
let anotherLong = "..."
// swiftlint:enable line_length
```

## Troubleshooting Table

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Warning persists after adding disable | Wrong line target (`:next` hit attribute/doc comment) | Use `:this` inline |
| `superfluous_disable_command` | Disable on wrong line | Move to function declaration line |
| `orphaned_doc_comment` | Disable comment between doc comment and function | Use `:this` inline instead |
| SwiftFormat undoes manual formatting | Rule conflict | Add `// swiftformat:disable:next <rule>` |
