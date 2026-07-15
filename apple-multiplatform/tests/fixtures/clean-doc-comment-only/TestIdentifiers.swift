// Regression: the audited symbols appear only inside comments.
//
// Field false positive (1 file). A doc comment reading "use .fullScreenCover"
// was reported as an unguarded macOS call. Comments must be stripped before
// symbol matching.
//
// Expect: zero hits.

import Foundation

enum FocusContainmentRules {
    /// Modal overlays that MUST contain focus (use .fullScreenCover).
    static let modals: Set<String> = [
        "HeadToHead",
        "ThemePicker",
    ]

    /* Block-comment form of the same trap:
       .fullScreenCover(isPresented: $flag) { ... }
       .tabViewStyle(.page)
       @Environment(\.editMode) private var editMode
     */

    /// Placement note: .topBarLeading is iOS-only chrome.
    static let placementNote = "see docs"
}
