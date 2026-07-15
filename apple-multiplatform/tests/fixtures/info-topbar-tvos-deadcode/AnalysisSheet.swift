// Info D2 — topBar placement reaching a tvOS compile.
//
// Also a real field finding. The `#if !os(tvOS)` closes before the `.toolbar`,
// so only `#if !os(macOS)` guards it — the indentation makes it look covered.
// Build-safe on both (`topBarLeading` is tvOS 14+, and macOS is excluded), but
// the Done button compiles for tvOS, where the HIG forbids Close/Done chrome.
//
// Expect: D2 info line, exit 0.

import SwiftUI

struct AnalysisSheet: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            Text("Analysis")
                .navigationTitle("Tier Analysis")
            #if !os(macOS)
                #if !os(tvOS)
                    .navigationBarTitleDisplayMode(.large)
                #endif
                    .toolbar {
                        ToolbarItem(placement: .topBarLeading) {
                            Button("Done") { dismiss() }
                        }
                    }
            #endif
        }
    }
}
