---
name: swift-file-splitting
author: eworthing
description: >-
  Splits oversized Swift files into smaller units while preserving visibility and
  build correctness. Use when a Swift file nears the SwiftLint `file_length`
  limit, when SwiftLint reports a `file_length` violation, when extracting types
  or extensions into new files, or when adding substantial code to an already
  large file.
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - Bash
---

# File Splitting

## Purpose

Split Swift files exceeding line limits while maintaining correct visibility modifiers for cross-file access. The most common gotcha: `private` properties break builds after extraction because they're invisible to extension files.

## When to Use

Use when:
- File exceeds 600 lines (400 for overlay files)
- SwiftLint reports a `file_length` violation
- User says "split this file", "too long", or "extract component"
- Logical grouping suggests separation

Do **not** use when:
- File is under 400 lines
- Splitting would create files under 100 lines
- The code is tightly coupled and splitting would hurt readability
- The file is generated code or a single declarative table (see [troubleshooting.md → escape hatch](references/troubleshooting.md#escape-hatch-when-you-should-not-split))

## Workflow

### Step 0: Commit Pending Work

Commit or stash any uncommitted changes first. A failed split is then reverted with `git restore .`.

```bash
git status
git add -A && git commit -m "wip: pre-split snapshot"
```

### Step 1: Inspect the File

Run the helper to surface line count, MARK boundaries, extensions, and private members in one pass:

```bash
scripts/pre-split-check.sh Sources/Views/SomeView.swift
```

Output flags any `private` / `fileprivate` members that will likely need their visibility widened.

### Step 2: Plan the Split

Choose boundaries from the helper's output. Prefer:

- Existing extension blocks → one file per extension
- MARK-delimited sections → one file per logical group
- Preview providers → `+Previews.swift`
- Protocol conformances → `+ProtocolName.swift`

See [examples.md](references/examples.md) for naming conventions and before/after patterns.

### Step 3: Widen Visibility Where Needed

For each `private` / `fileprivate` member that the new extension file will reference:

| Original | After split (if accessed cross-file) |
|----------|-------------------------------------|
| `private var` | `var` (or `internal var`) |
| `private func` | `func` (or `internal func`) |
| `fileprivate` | `internal` |

`fileprivate` does not bridge files; switching to `internal` is required.

### Step 4: Create the Extension File

```swift
// SomeView+Feature.swift
import SwiftUI

extension SomeView {
    // Extracted content here
}
```

Naming convention: `OriginalFile+Feature.swift`. Compound splits chain: `SomeView+Toolbar+PrimaryActions.swift`.

### Step 5: Move the Code

1. Copy the targeted block into the new file.
2. Update visibility per Step 3.
3. Remove the block from the original.
4. Add any needed imports to the new file.

### Step 6: Register With Xcode (if applicable)

SPM projects (`Package.swift` only): auto-discovered, skip this step.

`.xcodeproj` projects: see [xcodeproj.md](references/xcodeproj.md) for the three supported paths (XcodeGen, `xcodeproj` Ruby gem, or Xcode UI drag-in).

### Step 7: Build & Verify

```bash
xcodebuild build -scheme YourScheme -destination 'generic/platform=iOS'
wc -l Sources/Views/SomeView.swift Sources/Views/SomeView+Feature.swift
```

If the build fails, see [troubleshooting.md](references/troubleshooting.md) for the error-to-fix matrix. If verification looks wrong, `git restore .` to undo and re-plan.

## Common Mistakes

1. **Keeping `private` visibility** — must widen to `internal` for cross-file access.
2. **Splitting too granularly** — don't create files under 100 lines.
3. **Missing import statements** — the new file needs its own `import SwiftUI`, etc.
4. **Breaking MARK sections** — keep related code together; split *at* boundaries, not through them.
5. **Forgetting Xcode project updates** — `.xcodeproj` projects need `project.pbxproj` entries. See [xcodeproj.md](references/xcodeproj.md). SPM projects need nothing.
6. **Suppressing `file_length` instead of splitting** — only suppress when the file is genuinely an unsplittable declarative blob. See [troubleshooting.md → escape hatch](references/troubleshooting.md#escape-hatch-when-you-should-not-split).

## References

- [examples.md](references/examples.md) — before/after patterns, naming table, decision tree
- [xcodeproj.md](references/xcodeproj.md) — XcodeGen / `xcodeproj` gem / Xcode UI paths for pbxproj
- [troubleshooting.md](references/troubleshooting.md) — build-error → fix matrix, `swiftlint:disable file_length` escape hatch
- `scripts/pre-split-check.sh` — pre-flight inspection helper
- [`swift-linting`](../swift-linting/SKILL.md) skill — owns `.swiftlint.yml` rule rationale (including `file_length`)
- `.swiftlint.yml` in the consuming project — source of truth for the 600/400 thresholds

## Constraints

The 600/400 caps come from the consuming project's `.swiftlint.yml` `file_length` rule. Adjust limits there, not here.

- Main files: 600 lines max
- Overlay files: 400 lines max
- Minimum split result: 100 lines (smaller splits add navigation overhead without readability gain)
- Properties accessed cross-file must be `internal`, not `private`
