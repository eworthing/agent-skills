// Regression: local `#if os(tvOS)` around `.fullScreenCover`, with the macOS
// path in the `#else` branch using `.sheet`.
//
// Field false positive (4 files). The `#else` IS the macOS branch, but it names
// no platform, so a "must contain os(macOS)" check reports a correctly guarded
// file. This is the canonical fix the skill itself recommends.
//
// Expect: zero hits.

import SwiftUI

struct ThemeCreatorOverlay: View {
    @State private var showAdvancedPicker = false

    var body: some View {
        Button("Advanced") { showAdvancedPicker = true }
        #if os(tvOS)
            .fullScreenCover(isPresented: $showAdvancedPicker) {
                AdvancedPicker(isPresented: $showAdvancedPicker)
            }
        #else
            .sheet(isPresented: $showAdvancedPicker) {
                    AdvancedPicker(isPresented: $showAdvancedPicker)
                }
        #endif
    }
}

private struct AdvancedPicker: View {
    @Binding var isPresented: Bool

    var body: some View {
        Text("Picker")
    }
}
