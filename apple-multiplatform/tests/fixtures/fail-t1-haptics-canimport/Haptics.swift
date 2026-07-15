// True positive T1 — mirrors references/recovery.md E1/E4.
//
// canImport(UIKit) succeeds on tvOS, so this compiles there and the generator
// is unavailable at the symbol level. Must be #if os(iOS).
//
// Expect: T1 hit on the UIImpactFeedbackGenerator line.

import SwiftUI

#if canImport(UIKit)
    import UIKit

    struct HapticButton: View {
        var body: some View {
            Button("Tap") {
                UIImpactFeedbackGenerator(style: .medium).impactOccurred()
            }
        }
    }
#endif
