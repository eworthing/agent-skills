// Regression: three-way tabViewStyle chain with a macOS-safe `#else`.
//
// Field false positive (1 file). macOS lands in the `#else` and gets
// `.automatic`; `PageTabViewStyle` never enters a macOS compile. The old check
// demanded the literal string `os(macOS)`, which a correct `#else` need not
// contain — and spelling it `#elseif os(macOS)` would be worse code, dropping
// the visionOS/watchOS fallback.
//
// Expect: zero hits.

import SwiftUI

struct Wizard: View {
    @State private var page = 0

    var body: some View {
        TabView(selection: $page) {
            Text("One").tag(0)
            Text("Two").tag(1)
        }
        #if os(tvOS)
        .tabViewStyle(.page)
        .focusSection()
        #elseif os(iOS)
        .tabViewStyle(.page(indexDisplayMode: .never))
        #else
        .tabViewStyle(.automatic)
        #endif
    }
}
