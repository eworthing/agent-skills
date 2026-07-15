// True positive T1b — drag-and-drop receiving compiled for tvOS.
//
// `.onDrop` lists iOS / iPadOS / Mac Catalyst / macOS / visionOS — no tvOS.
// Ungated here, so it reaches a tvOS compile. Needs #if !os(tvOS).
//
// Expect: T1b hit on the .onDrop line.

import SwiftUI
import UniformTypeIdentifiers

struct DropTarget: View {
    var body: some View {
        Color.clear
            .onDrop(of: [UTType.image], isTargeted: nil) { _ in true }
    }
}
