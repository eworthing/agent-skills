// Regression: canImport branching for pasteboard, under an outer tvOS exclusion.
//
// `UIPasteboard` is unavailable on tvOS AND on native macOS. Here the outer
// `#if !os(tvOS)` removes tvOS, and `canImport(UIKit)` / `#elseif
// canImport(AppKit)` splits iOS from macOS. Correct on all three.
//
// Requires modelling canImport against the platform: canImport(UIKit) is FALSE
// on native macOS and TRUE on tvOS — so only the outer guard saves this file,
// and a checker that ignores canImport-vs-platform cannot tell.
//
// Expect: zero hits.

import SwiftUI

#if canImport(UIKit)
    import UIKit
#elseif canImport(AppKit)
    import AppKit
#endif

struct QRSheet: View {
    let url: URL

    var body: some View {
        Text(url.absoluteString)
    }

    #if !os(tvOS)
        func copyToPasteboard() {
            #if canImport(UIKit)
                UIPasteboard.general.string = url.absoluteString
            #elseif canImport(AppKit)
                NSPasteboard.general.clearContents()
                NSPasteboard.general.setString(url.absoluteString, forType: .string)
            #endif
        }
    #endif
}
