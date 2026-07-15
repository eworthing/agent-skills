// Regression: the app drives `\.editMode` itself on tvOS.
//
// Field false positive from D1's FIRST cut. D1 assumed "editMode compiles on
// tvOS but tvOS has no edit interface, therefore dead code". That premise only
// holds while nothing supplies the value. Here the app owns the state, injects
// it with `.environment(\.editMode, $editMode)`, toggles it from its own tvOS
// toolbar, and reads it back — a deliberate multi-select channel that happens to
// reuse SwiftUI's environment key. Every tvOS reader below is live.
//
// A shipping app does exactly this. D1 reported it as dead code and a reviewer
// acting on that report would have removed working tvOS behaviour.
//
// Expect: zero hits — no D1, because the tree injects editMode on a
// tvOS-compiled line.

import SwiftUI

struct MainAppView: View {
    #if os(iOS) || os(tvOS)
        @State var editMode: EditMode = .inactive
    #endif

    var body: some View {
        content
        #if os(iOS) || os(tvOS)
        .environment(\.editMode, $editMode)
        #endif
        .overlay(alignment: .bottom) {
            #if os(tvOS)
                ActionBar()
                    .environment(\.editMode, $editMode)
            #endif
        }
    }

    private var content: some View {
        Text("Grid")
    }

    /// Back/Menu handling depends on editMode being active on tvOS.
    func handleBack() -> Bool {
        #if os(iOS) || os(tvOS)
            if editMode == .active {
                editMode = .inactive
                return true
            }
        #endif
        return false
    }
}

#if os(tvOS)
    private struct ActionBar: View {
        @Environment(\.editMode) private var editMode

        var body: some View {
            if isMultiSelectActive {
                Text("Selected")
            }
        }

        private var isMultiSelectActive: Bool {
            editMode?.wrappedValue == .active
        }
    }
#endif
