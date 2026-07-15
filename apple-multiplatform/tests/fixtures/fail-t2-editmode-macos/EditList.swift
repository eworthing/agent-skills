// True positive T2 — editMode reaching a macOS compile.
//
// The bare `#if !os(tvOS)` is the classic wrong guard: it removes tvOS but
// leaves macOS, which has no editMode at all. Needs #if os(iOS).
//
// Expect: T2 hit on the @Environment(\.editMode) line.

import SwiftUI

struct EditList: View {
    #if !os(tvOS)
        @Environment(\.editMode) private var editMode
    #endif

    var body: some View {
        Text("List")
    }
}
