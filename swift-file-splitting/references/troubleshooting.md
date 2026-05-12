# Troubleshooting Post-Split Build Failures

Most post-split failures fall into a handful of categories. Match the symptom to the row, apply the fix.

## Build Error → Fix Matrix

| Error message (excerpt) | Cause | Fix |
|--------------------------|-------|-----|
| `'foo' is inaccessible due to 'private' protection level` | `private` member accessed from extension file | Change to `internal` (or drop the modifier). See [examples.md Example 3](examples.md#example-3-the-visibility-fix-pattern). |
| `cannot find 'foo' in scope` | Import statement missing in new file | Add `import SwiftUI` / `import Combine` / etc. to the top of the extension file. |
| `cannot find type 'Bar' in scope` | Nested type was extracted but is referenced by short name from the parent file | Either fully-qualify (`Parent.Bar`) or move the type back to the parent. |
| `extension declares a conformance ... already stated` | Conformance accidentally duplicated when copying | Remove the conformance from one of the two locations (usually keep on the extension file dedicated to that protocol). |
| `Build input file cannot be found: '...+Feature.swift'` | New file not added to the Xcode target | See [xcodeproj.md](xcodeproj.md) — file exists on disk but missing from `project.pbxproj`. |
| `'fileprivate' modifier cannot be used in an extension` (or similar visibility complaint) | `fileprivate` does not bridge files | Use `internal` instead. `fileprivate` only restricts to the *same source file*. |
| `circular reference` between original and extension | Property wrapper or computed property recursively references itself | Inspect the extracted member — usually a typo where the body references the property name instead of the backing store (`_value`). |
| Preview crashes but build succeeds | `#Preview` block references a member that's now `private` in another file | Move previews to a `+Previews.swift` extension, or relax visibility. |

## Diagnostic Commands

```bash
# Show all private/fileprivate members in the target file
grep -nE '(private|fileprivate) (var|let|func|class|struct|enum)' Sources/Views/SomeView.swift

# Show what's been added to the new extension file
diff -u /dev/null Sources/Views/SomeView+Feature.swift | head -50

# Confirm both files in the build graph (after pbxproj update)
xcodebuild -list -project MyApp.xcodeproj
```

## Escape Hatch: When You Should NOT Split

Sometimes a `file_length` warning is the wrong signal. Splitting hurts more than it helps when:

- The file is a single declarative table (generated grammar, AST node enumerations, exhaustive type maps).
- The split would create cross-file references that fight the type system (e.g. nested generic types).
- The file is auto-generated and would be overwritten on next regeneration.

In those cases, suppress the warning at the file level:

```swift
// swiftlint:disable file_length
// Reason: <one-line justification — table-driven grammar, generated code, etc.>

// ... file contents ...

// swiftlint:enable file_length
```

Or, for an entire generated directory, add to `.swiftlint.yml`:

```yaml
excluded:
  - Sources/Generated
```

**Do not** disable `file_length` to avoid a refactor you simply don't want to do. The escape hatch is for cases where splitting genuinely degrades the code.

## When in Doubt

Revert the split with `git restore .` (assumes you committed before splitting per Step 0 of the workflow), then re-examine boundaries. A failed split is cheap to undo when the working tree was clean going in.
