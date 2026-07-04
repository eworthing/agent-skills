# Configuring the export/save dialog

These modifiers refine the panel that `.fileExporter` presents. Attach them to the
**same view the `.fileExporter` is on** (the root view — see Critical Rule #1 in
SKILL.md). Most have a visible effect only on macOS's `NSSavePanel`; on iOS/iPadOS the
document picker ignores the ones that don't map to it, so they're safe to attach
unconditionally but only *pay off* on macOS.

All of the modifiers below are **iOS 17+ / iPadOS 17+ / Mac Catalyst 17+ / macOS 14+ /
visionOS 1+.** On an iOS 16 / macOS 13 floor, gate them (`if #available` or a
`#if compiler` guard) or the build fails.

| Modifier | What it changes |
|----------|-----------------|
| `fileExporterFilenameLabel(_:)` | The label next to the filename field (macOS). |
| `fileDialogDefaultDirectory(_:)` | The directory the panel opens in. Ignored if the panel has a `fileDialogCustomizationID` and the user already chose a directory. |
| `fileDialogConfirmationLabel(_:)` | The confirmation button title (e.g. "Export" instead of "Save"). |
| `fileDialogMessage(_:)` | A message string shown in the panel. |
| `fileDialogBrowserOptions(_:)` | `FileDialogBrowserOptions` — e.g. show/hide hidden files, allow choosing directories. |
| `fileDialogCustomizationID(_:)` | A stable ID so the panel remembers size/position/last-directory across launches. |

## Combined example

```swift
ContentView()
    .fileExporter(
        isPresented: $showExporter,
        item: pendingExportItem,
        contentTypes: [.json, .commaSeparatedText],
        defaultFilename: pendingExportItem?.filename ?? "Export",
        onCompletion: handleExportResult,
        onCancellation: { logger.info("Export cancelled") }
    )
    .fileExporterFilenameLabel("Export as")
    .fileDialogDefaultDirectory(.documentsDirectory)
    .fileDialogConfirmationLabel("Export")
    .fileDialogCustomizationID("com.example.export-panel")
```

## Notes

- `fileDialogCustomizationID` is what makes a panel "sticky" — reuse the **same** ID for
  the same logical panel so macOS restores the user's last folder. A new ID each
  presentation resets it every time.
- `fileDialogDefaultDirectory` is a *starting* directory only; the sandbox still requires
  the user to confirm the actual save location (Critical Rule #2 in SKILL.md).
- These modifiers configure both `.fileExporter` and `.fileImporter` panels; this skill
  only covers the export side.
