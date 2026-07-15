// Regression: the textbook-correct haptics pattern the skill itself documents.
//
// Field false positive (8 hits in one file). `canImport(UIKit)` wraps ONLY the
// import — every generator use sits inside `#if os(iOS)`, and tvOS falls through
// to a no-op. The old check flagged the file merely for co-locating
// `canImport(UIKit)` with the symbol names, two of which were in a doc comment.
//
// Expect: zero hits.

import Foundation

#if canImport(UIKit)
    import UIKit
#endif

#if canImport(AppKit)
    import AppKit
#endif

protocol HapticFeedback {
    var isAvailable: Bool { get }
    func impact()
}

#if os(iOS)
    /// iOS haptics.
    ///
    /// Uses `UIImpactFeedbackGenerator`, `UISelectionFeedbackGenerator`, and
    /// `UINotificationFeedbackGenerator` to provide haptic feedback.
    struct UIKitHapticFeedback: HapticFeedback {
        private let lightImpact = UIImpactFeedbackGenerator(style: .light)
        private let selection = UISelectionFeedbackGenerator()
        private let notification = UINotificationFeedbackGenerator()

        var isAvailable: Bool {
            true
        }

        func impact() {
            lightImpact.impactOccurred()
        }
    }
#endif

#if os(macOS)
    struct AppKitHapticFeedback: HapticFeedback {
        var isAvailable: Bool {
            true
        }

        func impact() {
            NSHapticFeedbackManager.defaultPerformer.perform(.generic, performanceTime: .default)
        }
    }
#endif

/// tvOS and other platforms: no haptic hardware available.
struct NoOpHapticFeedback: HapticFeedback {
    var isAvailable: Bool {
        false
    }

    func impact() {}
}

func makeHapticFeedback() -> HapticFeedback {
    #if os(iOS)
        return UIKitHapticFeedback()
    #elseif os(macOS)
        return AppKitHapticFeedback()
    #else
        return NoOpHapticFeedback()
    #endif
}
