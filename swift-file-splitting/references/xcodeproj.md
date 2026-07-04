# Adding New Files to an Xcode Project

SPM-only projects (`Package.swift`, no `.xcodeproj`) auto-discover sources under declared target paths — **skip this entire reference**.

For `.xcodeproj` projects, whether a new `.swift` file needs a `project.pbxproj` entry depends on **where the file lands**, not on the project as a whole. Check Path 0 first; only if it doesn't apply do you need the legacy group-based paths.

## Path 0 — Buildable folders (Xcode 16+)

Since Xcode 16, a group can be a **file-system synchronized group** (`PBXFileSystemSynchronizedRootGroup`) — a "buildable folder" that stores only the folder path. Xcode auto-adds every on-disk file **under that folder** to the owning target, so a new file there needs **zero** registration. This is a **two-step** check, because a project can *mix* buildable folders and legacy yellow groups — "the project has synchronized groups" does **not** by itself mean *your* new file is auto-included.

**Step A — does the project use synchronized groups at all?**

```bash
grep -q PBXFileSystemSynchronizedRootGroup MyApp.xcodeproj/project.pbxproj \
  && echo "project uses buildable folders (may be mixed with legacy groups)"
```

**Step B — is the new file under a synchronized folder?** The auto-include applies only when the file's directory is (under) a folder Xcode synchronizes. Confirm by the **visual cue** — in the Project Navigator that folder shows as a plain **blue folder**, not a yellow group. (Matching the file's parent dir against the synchronized root paths inside `project.pbxproj` is fiddly and error-prone; the reliable check is the blue-folder cue plus a build.)

**Headless fallback (no Xcode UI):** when you can't see the navigator and can't confirm the synchronized root path from the pbxproj, treat the result as **inconclusive** — do a normal build to confirm the new file compiles into the target before assuming the skip. If it's missing from the build, fall through to the legacy paths below.

**Rule (conditional):**
- New file **inside** a synchronized folder's path → auto-included, **skip all registration** (no gem, no pbxproj edit, no drag-in).
- Project is mixed and the file is under a **yellow group** → it still needs registration; use the legacy paths below.

**Exception note:** individual files can be *excluded* from a synchronized folder via `PBXFileSystemSynchronizedBuildFileExceptionSet` (e.g. `README`, `Fastfile`). A new `.swift` sibling of already-built sources is included by default.

## Legacy group-based registration

If the project uses yellow groups, or the new file is **not** under a synchronized folder, register it via one of the three paths below (in order of preference).

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

A file confirmed under a **buildable folder** (Path 0) needs no verification beyond a normal build — if it compiles, it's in the target. For the legacy paths, after adding, confirm:

```bash
xcodebuild -showBuildSettings -scheme YourScheme | grep -q "OK" \
  && xcodebuild build -scheme YourScheme -destination 'generic/platform=iOS' \
     -dry-run 2>&1 | grep -q "SomeView+Feature.swift"
```

If the new file does not appear in the dry-run output, the target membership is missing.
