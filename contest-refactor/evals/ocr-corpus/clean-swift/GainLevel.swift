import Foundation

/// Playback gain. Non-finite input is rejected *before* the clamp runs, so
/// the invariant queue's `clamp_unchecked` signal (garbage-in-the-wrong-
/// direction via `min`/`max`) must never fire here.
public struct GainLevel: Hashable, Sendable, RawRepresentable {
    public let rawValue: Double

    public init(rawValue: Double) {
        self.rawValue = rawValue.isFinite ? max(0, min(2, rawValue)) : 0
    }

    public static let unity = GainLevel(rawValue: 1.0)
}
