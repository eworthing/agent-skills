// True positive T5 — mirrors references/recovery.md E8.
//
// .fullScreenCover is unavailable on macOS; ungated here. Needs a .sheet branch.
//
// Expect: T5 hit on the .fullScreenCover line.

import SwiftUI

struct Modal: View {
    @State private var show = false

    var body: some View {
        Button("Open") { show = true }
            .fullScreenCover(isPresented: $show) {
                Text("Content")
            }
    }
}
