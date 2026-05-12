# Adding New Files to an Xcode Project

SPM-only projects (`Package.swift`, no `.xcodeproj`) auto-discover sources under declared target paths — **skip this entire reference**.

For `.xcodeproj` projects, new `.swift` files need entries in `project.pbxproj`. Three workable paths, in order of preference:

## 1. XcodeGen (preferred when available)

If the repo already uses XcodeGen (a `project.yml` file at root), regenerate the project:

```bash
xcodegen generate
```

New files in declared source paths are picked up automatically. No `pbxproj` editing.

## 2. `xcodeproj` Ruby Gem (scriptable, repeatable)

Install once:

```bash
gem install xcodeproj
```

Then script the additions:

```ruby
require 'xcodeproj'

project_path = 'MyApp.xcodeproj'
project = Xcodeproj::Project.open(project_path)

target = project.targets.find { |t| t.name == 'MyApp' }
group  = project.main_group.find_subpath('Sources/Views', true)

new_file = 'Sources/Views/SomeView+Feature.swift'
file_ref = group.new_file(new_file)
target.add_file_references([file_ref])

project.save
```

This path is repeatable and reviewable. Good for split workflows that touch many files.

## 3. Xcode UI Drag-In (fastest for one-offs)

1. Create the file on disk first (e.g. via `Write` tool).
2. Open the project in Xcode.
3. Drag the new file into the appropriate group in the navigator.
4. In the dialog:
   - **Uncheck** "Copy items if needed" (file is already in place).
   - **Check** the correct target membership.

## Anti-Pattern: Hand-Editing project.pbxproj

`project.pbxproj` uses unique 24-char hex IDs across four parallel sections:

- `PBXBuildFile`
- `PBXFileReference`
- `PBXGroup` (children array)
- `PBXSourcesBuildPhase` (files array)

A single typo or missing reference corrupts the project, often with cryptic errors. Avoid manual edits unless you understand the format intimately.

## Verifying the File Is in the Build

After adding, confirm:

```bash
xcodebuild -showBuildSettings -scheme YourScheme | grep -q "OK" \
  && xcodebuild build -scheme YourScheme -destination 'generic/platform=iOS' \
     -dry-run 2>&1 | grep -q "SomeView+Feature.swift"
```

If the new file does not appear in the dry-run output, the target membership is missing.
