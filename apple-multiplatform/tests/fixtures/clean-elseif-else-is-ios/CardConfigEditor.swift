// Regression: `#elseif` inversion — `#if os(tvOS)` / `#elseif os(macOS)` / `#else`.
//
// The `#else` here means "neither tvOS nor macOS" — i.e. iOS — so the
// `.topBarLeading` toolbar and `EditButton` never reach a macOS compile.
//
// A hand-rolled scanner written during the field review got exactly this wrong:
// it treated the `#else` as a plain negation of the immediately preceding
// `#elseif` and reported a macOS break. `#elseif C` must become
// NOT(any earlier branch) AND C for the `#else` to resolve correctly.
//
// Expect: zero hits.

import SwiftUI

struct CardConfigEditor: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        #if os(tvOS)
            tvOSBody
        #elseif os(macOS)
            macOSBody
        #else
            NavigationStack {
                contentBody
                    .toolbar {
                        ToolbarItem(placement: .topBarLeading) {
                            EditButton()
                        }
                        ToolbarItem(placement: .confirmationAction) {
                            Button("Done") { dismiss() }
                        }
                    }
            }
        #endif
    }

    private var contentBody: some View {
        Text("Config")
    }

    #if os(tvOS)
        private var tvOSBody: some View {
            Text("Config")
                .onExitCommand { dismiss() }
        }
    #endif

    #if os(macOS)
        private var macOSBody: some View {
            Text("Config")
        }
    #endif
}
