// True positive T4 — mirrors references/recovery.md E2.
//
// .topBarLeading is unavailable on macOS; ungated here.
//
// Expect: T4 hit on the .topBarLeading line (plus a D2 info line for tvOS).

import SwiftUI

struct ToolbarHost: View {
    var body: some View {
        Text("Content")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Edit") {}
                }
            }
    }
}
