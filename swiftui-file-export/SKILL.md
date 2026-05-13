---
name: swiftui-file-export
author: eworthing
description: >-
  SwiftUI file export patterns using the modern Transferable API on iOS 16+,
  iPadOS 16+, and macOS 13+. Covers fileExporter root-placement rules,
  Transferable conformance for single and multiple formats, ShareLink vs.
  fileExporter selection, sandbox compliance, macOS entitlements, menu-bar
  Commands integration, and tvOS gating. Use when implementing file export,
  Transferable, fileExporter, ShareLink, NSSavePanel, sandbox compliance,
  macOS save panel, CSV/JSON/Markdown export, document export, menu bar
  export commands, multi-format exports, or diagnosing fileExporter silent
  failure on macOS.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---

# SwiftUI File Export Patterns

## Purpose

SwiftUI ships a first-class export API on iOS 16+ / iPadOS 16+ / macOS 13+
built on `Transferable` and `.fileExporter`. Used correctly, it works
inside the App Sandbox without extra entitlements beyond the standard
user-selected file read/write key. Used incorrectly, exports silently fail
on macOS or trip sandbox violations. This skill captures the placement,
state, and platform rules that matter.

## When to Use

- Adding a new export format (JSON, CSV, plain text, Markdown, PDF, etc.)
- Diagnosing exports that work on iOS but silently fail on macOS
- Wiring menu-bar `Commands` that trigger an export
- Choosing between `ShareLink` and `.fileExporter`
- Auditing sandbox / entitlement issues in an export path

## Do NOT Use For

- Importing files (`.fileImporter` has its own gotchas)
- Server-side or non-user-driven writes
- tvOS-only apps (no file export API is available)

---

## Critical Rule #1: `.fileExporter` MUST Be at the Root View Level

On macOS, `.fileExporter` presents an `NSSavePanel` that runs out-of-process.
Nesting it inside `.sheet`, `.popover`, `.inspector`, or `.alert` puts the
panel in the wrong window-layer hierarchy and the panel will fail to appear,
appear behind the sheet, or dismiss immediately.

```swift
// WRONG — fileExporter nested inside a sheet
.sheet(isPresented: $showExportSheet) {
    ExportFormatPicker()
        .fileExporter(isPresented: $showExporter, ...) // BROKEN on macOS
}

// CORRECT — fileExporter attached at the root view
struct RootView: View {
    @State private var showFileExporter = false
    @State private var pendingExportItem: DocumentExportItem?

    var body: some View {
        ContentView()
            .fileExporter(
                isPresented: $showFileExporter,
                item: pendingExportItem,
                contentTypes: [.json, .commaSeparatedText, .plainText],
                defaultFilename: pendingExportItem?.filename ?? "Export"
            ) { result in
                handleExportResult(result)
            }
    }
}
```

The same rule applies on iOS — keeping `.fileExporter` at the root simplifies
state and avoids re-entrancy issues when the picker dismisses.

---

## Critical Rule #2: Never Direct-Write to User Directories

The App Sandbox blocks writes to `~/Documents`, `~/Downloads`, and similar
locations unless the user grants access through a system picker. Bypassing
that with `FileManager` will either fail outright or require risky
entitlements.

```swift
// WRONG — bypasses the sandbox, requires extra entitlements, breaks on macOS
let path = NSHomeDirectory() + "/Downloads/export.json"
FileManager.default.createFile(atPath: path, contents: data)

// CORRECT — fileExporter receives a user-granted URL with extended access
.fileExporter(isPresented: $showExporter, item: exportItem, ...) { result in
    switch result {
    case .success(let url):
        logger.info("Saved export to \(url.path, privacy: .public)")
    case .failure(let error):
        logger.error("Export failed: \(error.localizedDescription)")
    }
}
```

`.fileExporter` extends the sandbox scope automatically for the chosen URL.

---

## Critical Rule #3: Menu Bar Commands Route Through Observable State

`Commands` (`.commands { CommandGroup… }`) attach to the `Scene`, not to a
specific view, so they cannot present `.fileExporter` themselves. The
correct pattern is to mutate observable state that the root view is already
binding to.

```swift
// WRONG — Commands cannot present .fileExporter directly
CommandGroup(after: .saveItem) {
    Button("Export as JSON") {
        // No view scope here; writing directly bypasses sandbox
        try? data.write(to: someURL)
    }
}

// CORRECT — Commands set state observed by the root view
CommandGroup(after: .saveItem) {
    Button("Export as JSON") {
        exportCoordinator.pendingExportItem = DocumentExportItem(
            data: jsonData,
            filename: "export.json",
            contentType: .json
        )
        exportCoordinator.showFileExporter = true
    }
    .keyboardShortcut("E", modifiers: [.command, .shift])
}
```

`exportCoordinator` is an `@Observable` (or `ObservableObject`) instance
owned at the `App` / `Scene` level and injected via `.environment(...)`.

---

## Transferable Implementation

### Single Format

```swift
import CoreTransferable
import UniformTypeIdentifiers

struct DocumentExportItem: Transferable {
    let data: Data
    let filename: String
    let contentType: UTType

    static var transferRepresentation: some TransferRepresentation {
        DataRepresentation(exportedContentType: .json) { item in
            item.data
        }
        .suggestedFileName { item in item.filename }
    }
}
```

### Multiple Formats (Chained `DataRepresentation`)

When a single item can be exported as several types, declare one
`DataRepresentation` per content type. The exporter picks the matching one
based on `contentTypes:` passed to `.fileExporter` and the user's choice in
the save panel.

```swift
struct DocumentExportItem: Transferable {
    let json: Data
    let csv: Data
    let plain: Data
    let filename: String

    static var transferRepresentation: some TransferRepresentation {
        DataRepresentation(exportedContentType: .json) { $0.json }
            .suggestedFileName { $0.filename + ".json" }

        DataRepresentation(exportedContentType: .commaSeparatedText) { $0.csv }
            .suggestedFileName { $0.filename + ".csv" }

        DataRepresentation(exportedContentType: .plainText) { $0.plain }
            .suggestedFileName { $0.filename + ".txt" }
    }
}
```

---

## ShareLink vs. `.fileExporter`

| Scenario                              | ShareLink | fileExporter |
|---------------------------------------|-----------|--------------|
| Share via AirDrop / Messages / Mail   | yes       | no           |
| Save to a specific location           | no        | yes          |
| User chooses save location explicitly | no        | yes          |
| Quick share without saving            | yes       | no           |
| Multi-format save panel               | limited   | yes          |

When both make sense, offer them side-by-side:

```swift
HStack {
    ShareLink(item: exportItem, preview: SharePreview(exportItem.filename)) {
        Label("Share", systemImage: "square.and.arrow.up")
    }

    Button("Save to Files...") {
        exportCoordinator.pendingExportItem = exportItem
        exportCoordinator.showFileExporter = true
    }
}
```

---

## Platform Behaviors

| Platform   | `.fileExporter`        | `ShareLink`       |
|------------|------------------------|-------------------|
| iOS/iPadOS | Document picker sheet  | Share sheet       |
| macOS      | `NSSavePanel`          | Share menu        |
| tvOS       | Not available          | Not available     |

---

## macOS Entitlements

The only entitlement required for `.fileExporter`:

```xml
<key>com.apple.security.files.user-selected.read-write</key>
<true/>
```

Do NOT add `com.apple.security.files.downloads.read-write` — it grants
broader access than needed and is unnecessary because `.fileExporter`
already extends the sandbox to the user-chosen URL.

---

## Export State Flow

1. User picks a format in a format-picker view, or invokes a menu command.
2. Build a `Transferable` item (`DocumentExportItem`) with data, filename,
   and `UTType`.
3. Set `coordinator.pendingExportItem = item`.
4. Set `coordinator.showFileExporter = true`.
5. The root view's `.fileExporter` presents the document picker (iOS) or
   `NSSavePanel` (macOS).
6. The system extends the sandbox scope to the user-selected URL.
7. The completion handler receives `Result<URL, Error>` — log success and
   surface failures.

---

## tvOS Handling

`.fileExporter`, `ShareLink`, and `UIActivityViewController` are unavailable
on tvOS. Gate export UI with `#if os(tvOS)` and either hide the entry point
or show an informational state.

```swift
#if !os(tvOS)
Button("Export...") { showExporter = true }
#endif
```

For shared code that generates export payloads, the data layer can stay
cross-platform; only the presentation layer needs the gate.

---

## Debugging Export Failures

| Symptom                                   | Check                                                                                  |
|-------------------------------------------|----------------------------------------------------------------------------------------|
| macOS export silently fails / no panel    | Is `.fileExporter` at the root view (not inside `.sheet`/`.popover`/`.inspector`)?     |
| Picker dismisses immediately on macOS     | Is the `item` non-nil at the moment `isPresented` flips to `true`?                     |
| Sandbox violation in Console.app          | Confirm no `FileManager` direct-write to `~/Downloads` or `NSHomeDirectory()`.         |
| Works on iOS, fails on macOS              | Are menu-bar Commands routing through state instead of writing files directly?         |
| "Operation not permitted" at save time    | Verify `com.apple.security.files.user-selected.read-write` is in the .entitlements.   |
| Wrong file extension                      | Each `DataRepresentation` needs its own `.suggestedFileName { ... }` for that type.   |
| `Transferable` doesn't expose a format    | Add a chained `DataRepresentation(exportedContentType: .X)` for that `UTType`.        |

---

## References

- WWDC22 — "Meet Transferable" (Apple, 2022)
- Apple developer docs: `Transferable`, `DataRepresentation`, `FileDocument`
- Apple developer docs: `View.fileExporter(isPresented:item:contentTypes:defaultFilename:onCompletion:)`
- Apple developer docs: `ShareLink`
- Apple developer docs: App Sandbox — `com.apple.security.files.user-selected.read-write`

---

## Constraints

- NEVER write to user directories via `FileManager` — always route through
  `.fileExporter` or `ShareLink`.
- ALWAYS attach `.fileExporter` at the root view, never inside a modal.
- ALWAYS route menu-bar export Commands through observable state owned at
  the `Scene` level.
- Test every export on BOTH iOS and macOS; macOS reveals the placement and
  entitlement issues iOS hides.
- tvOS has no file export — gate with `#if !os(tvOS)`.
