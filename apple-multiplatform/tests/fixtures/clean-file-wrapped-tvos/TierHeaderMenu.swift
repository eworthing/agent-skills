// Regression: whole-file `#if os(tvOS)` wrap around a `.fullScreenCover`.
//
// Field false positive (5 files). The old file-scoped check asked "does the
// string `os(macOS)` appear in this file?" — it does not, because `#if os(tvOS)`
// excludes macOS without naming it. Correct code, flagged as a macOS break.
//
// Expect: zero hits.

import SwiftUI

#if os(tvOS)
    struct TierHeaderMenu: View {
        @State private var showMenu = false

        var body: some View {
            Button("Menu") { showMenu = true }
                .fullScreenCover(isPresented: $showMenu, content: {
                    MenuContent(isPresented: $showMenu)
                })
        }
    }

    private struct MenuContent: View {
        @Binding var isPresented: Bool

        var body: some View {
            Text("Menu")
                .onExitCommand { isPresented = false }
        }
    }
#endif
