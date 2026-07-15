// Info D1 — editMode gated `#if os(iOS) || os(tvOS)`.
//
// This is a real defect found by hand during the field review, which the old
// script could not see. Build-safe (macOS is excluded), so it is NOT a failure
// — but editMode compiles on tvOS (symbol exists since tvOS 13) while tvOS has
// no edit interface, so nothing ever sets it and the branch is unreachable.
// Narrowing to `#if os(iOS)` removes the dead code.
//
// Expect: D1 info line, exit 0 (info hits must not fail a gate).

import SwiftUI

struct TierMoveSheet: View {
    #if os(iOS) || os(tvOS)
        @Environment(\.editMode) private var editMode
    #endif

    private let allTiers = ["S", "A", "B"]
    private let isBatchMode = false

    var body: some View {
        Text("Move")
    }

    private var defaultFocusTier: String? {
        #if os(iOS) || os(tvOS)
            if let editMode, editMode.wrappedValue == .active, !isBatchMode {
                return allTiers.first
            }
        #endif
        return allTiers.first
    }
}
