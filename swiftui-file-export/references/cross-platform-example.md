# End-to-end export example (App + Scene + Commands)

A complete, self-consistent sample wiring every rule from SKILL.md together: the
`.fileExporter` at the root (Rule #1), no `FileManager` direct-write (Rule #2), and
menu-bar `Commands` routed through observable state (Rule #3). The fragments in
SKILL.md all point here for the full picture.

**Deployment target for this sample: iOS 17+ / iPadOS 17+ / macOS 14+ / visionOS 1+**
(uses the `onCancellation:` overload, iOS 17 / macOS 14). On an iOS 16 / macOS 13 floor,
drop the `onCancellation:` argument — the `onCompletion:`-only overload is iOS 16+.

## The Transferable payload

```swift
import CoreTransferable
import UniformTypeIdentifiers

struct DocumentExportItem: Transferable {
    let data: Data
    let filename: String
    let contentType: UTType

    static var transferRepresentation: some TransferRepresentation {
        DataRepresentation(exportedContentType: .json) { $0.data }
            .suggestedFileName { $0.filename }
    }
}
```

## The coordinator

A single source of truth for "what to export" and "is the panel up," owned at the
`App` level and injected into the environment. `@Observable @MainActor` — export UI is
main-actor state; there is no reason to make it `ObservableObject` on a modern target.

```swift
import SwiftUI
import OSLog

@Observable
@MainActor
final class ExportCoordinator {
    var pendingExportItem: DocumentExportItem?
    var showFileExporter = false

    let logger = Logger(subsystem: "com.example.app", category: "export")

    func requestExport(_ item: DocumentExportItem) {
        pendingExportItem = item
        showFileExporter = true
    }

    func handleResult(_ result: Result<URL, Error>) {
        switch result {
        case .success(let url):
            logger.info("Saved export to \(url.path, privacy: .public)")
        case .failure(let error):
            logger.error("Export failed: \(error.localizedDescription)")
        }
        pendingExportItem = nil
    }
}
```

## The App, root view, and Commands

```swift
@main
struct ExampleApp: App {
    @State private var exportCoordinator = ExportCoordinator()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(exportCoordinator)   // inject once, at the root
        }
        #if os(macOS)
        .commands {
            CommandGroup(after: .saveItem) {
                Button("Export as JSON") {
                    let item = DocumentExportItem(
                        data: buildJSON(),
                        filename: "export.json",
                        contentType: .json
                    )
                    exportCoordinator.requestExport(item)   // Rule #3: route through state
                }
                .keyboardShortcut("E", modifiers: [.command, .shift])
            }
        }
        #endif
    }
}

struct RootView: View {
    @Environment(ExportCoordinator.self) private var exportCoordinator

    var body: some View {
        @Bindable var coordinator = exportCoordinator   // bind the @Observable for $-bindings

        ContentView()
            // Rule #1: fileExporter attached at the ROOT, never inside a sheet/popover.
            .fileExporter(
                isPresented: $coordinator.showFileExporter,
                item: coordinator.pendingExportItem,
                contentTypes: [.json],
                defaultFilename: coordinator.pendingExportItem?.filename ?? "Export",
                onCompletion: { coordinator.handleResult($0) },
                onCancellation: { coordinator.logger.info("Export cancelled by user") }
            )
    }
}
```

## The in-view entry point (and tvOS gate)

```swift
struct ContentView: View {
    @Environment(ExportCoordinator.self) private var exportCoordinator

    var body: some View {
        VStack {
            // ... app content ...

            #if !os(tvOS)   // tvOS has no file export API
            Button("Export...") {
                let item = DocumentExportItem(
                    data: buildJSON(),
                    filename: "export.json",
                    contentType: .json
                )
                exportCoordinator.requestExport(item)
            }
            #endif
        }
    }
}
```

The data layer (`buildJSON()` and friends) stays fully cross-platform; only the
presentation entry points need the `#if !os(tvOS)` gate.

## The entitlement (macOS)

The `.entitlements` file needs exactly one key — do **not** add
`com.apple.security.files.downloads.read-write` (see SKILL.md → macOS Entitlements):

```xml
<key>com.apple.security.files.user-selected.read-write</key>
<true/>
```

`.fileExporter` extends the sandbox scope to the user-chosen URL automatically; the
user-selected read-write key is all that's required.
