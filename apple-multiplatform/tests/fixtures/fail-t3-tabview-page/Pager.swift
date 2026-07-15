// True positive T3 — mirrors references/recovery.md E6.
//
// PageTabViewStyle is unavailable on macOS; ungated here.
//
// Expect: T3 hit on the .tabViewStyle(.page) line.

import SwiftUI

struct Pager: View {
    var body: some View {
        TabView {
            Text("One")
            Text("Two")
        }
        .tabViewStyle(.page)
    }
}
