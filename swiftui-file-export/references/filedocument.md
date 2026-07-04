# FileDocument vs. ad-hoc Transferable

The main SKILL.md teaches the ad-hoc `Transferable` path (`DocumentExportItem`) —
the right tool when you export a snapshot of data from a screen that is **not** a
document-based app. This file covers the `FileDocument` path and when to prefer it,
plus multi-**document** batch export and the reference-type story.

## When each wins

| Situation | Use |
|-----------|-----|
| Export a one-shot data blob (report, CSV, current view state) from a normal app | ad-hoc `Transferable` (`DocumentExportItem`) — see SKILL.md |
| The value **is** the app's document model (a file the user opens, edits, saves) | `FileDocument` + the `.fileExporter(...document:...)` overload |
| Save several already-built documents in one panel | `documents:` / `items:` batch overloads (below) |
| Reference-type (class) document model | see [Reference-type documents](#reference-type-documents) — mostly out of scope |

`FileDocument` buys you the document lifecycle (`DocumentGroup`, open/save panels,
undo, rename) that the ad-hoc path doesn't. If you only need "turn this data into a
file the user picks a location for," the ad-hoc `Transferable` path is simpler and
carries less ceremony — don't reach for `FileDocument` just to export a blob.

## FileDocument (value type)

`FileDocument` is a value-type document model. **iOS 14+ / iPadOS 14+ / macOS 11+ /
visionOS 1+.** Not deprecated. It must be `Sendable` — SwiftUI calls its
serialization methods off `MainActor`, so don't touch main-actor state inside them.

```swift
import SwiftUI
import UniformTypeIdentifiers

struct TextFile: FileDocument {
    // Types this document can be READ from.
    static let readableContentTypes: [UTType] = [.plainText]
    // Types this document can be WRITTEN to. If omitted, defaults to readableContentTypes.
    static let writableContentTypes: [UTType] = [.plainText]

    var text: String

    init(text: String = "") { self.text = text }

    // Deserialize — called off the main actor.
    init(configuration: ReadConfiguration) throws {
        guard let data = configuration.file.regularFileContents,
              let string = String(data: data, encoding: .utf8)
        else { throw CocoaError(.fileReadCorruptFile) }
        text = string
    }

    // Serialize — called off the main actor.
    func fileWrapper(configuration: WriteConfiguration) throws -> FileWrapper {
        FileWrapper(regularFileWithContents: Data(text.utf8))
    }
}
```

Export it with the document overload. The `contentType` you pass **must be a member
of `writableContentTypes`**, otherwise SwiftUI silently falls back to the first
writable type:

```swift
// iOS 14+ / macOS 11+ — no cancellation callback on this overload.
.fileExporter(
    isPresented: $showExporter,
    document: pendingDocument,           // a TextFile?
    contentType: .plainText,
    defaultFilename: "Notes"
) { result in
    handleExportResult(result)
}
```

The dialog only appears when **both** `isPresented == true` **and** `document != nil`.

## onCancellation on the document overload

Like the `item:` path, the document overload gained an `onCancellation:` variant in
**iOS 17 / macOS 14** (`fileExporter(isPresented:document:contentType:defaultFilename:onCompletion:onCancellation:)`).
Use it to observe user-cancel instead of letting it vanish. On an iOS 16 / macOS 13
floor the callback isn't available — gate it:

```swift
#if compiler(>=5.9)  // shipped with the iOS 17 / macOS 14 SDK
.fileExporter(
    isPresented: $showExporter,
    document: pendingDocument,
    contentType: .plainText,
    defaultFilename: "Notes",
    onCompletion: handleExportResult,
    onCancellation: { logger.info("Export cancelled by user") }
)
#endif
```

## Multi-document batch export

To write **several documents** in one operation (distinct from "one item, several
formats" in SKILL.md, which is one document offered as multiple UTTypes), use the
plural overloads:

- `fileExporter(isPresented:documents:contentType:onCompletion:)` — a collection of `FileDocument`s.
- `fileExporter(isPresented:items:contentTypes:onCompletion:onCancellation:)` — a collection of `Transferable`s (iOS 17+ / macOS 14+).

```swift
.fileExporter(
    isPresented: $showBatchExporter,
    documents: pendingDocuments,         // [TextFile]
    contentType: .plainText
) { result in
    switch result {
    case .success(let urls): logger.info("Exported \(urls.count) files")
    case .failure(let error): logger.error("Batch export failed: \(error.localizedDescription)")
    }
}
```

The batch overload presents a directory-chooser rather than a per-file save panel.

## Reference-type documents

For **class**-based document models the historical protocol is `ReferenceFileDocument`
(iOS 14+ / macOS 11+). **It is deprecated as of the iOS 27 / macOS 27 SDK.** The modern
replacements live in the SwiftUI *Documents* API collection:

- `Document` with the `ReadableDocument` / `WritableDocument` protocols — URL-based,
  Swift-concurrency-native, progress-reporting.
- SwiftData-backed documents via `DocumentGroup(editing:contentType:editor:...)`.

Full document-based-app territory (`DocumentGroup`, launch scenes, open/rename actions)
is **adjacent to this skill, not part of it** — this skill is about *exporting* data
via `.fileExporter` / `ShareLink`, not standing up a document app. If you're building a
document app, start from Apple's *Documents* collection
(<https://developer.apple.com/documentation/swiftui/documents>) and use `FileDocument`
for value types. On a deployment target below iOS 27, `ReferenceFileDocument` remains
usable (with the deprecation warning); on iOS 27+, prefer `ReadableDocument` /
`WritableDocument`.
