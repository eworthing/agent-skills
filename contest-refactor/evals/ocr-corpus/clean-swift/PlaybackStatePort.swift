import Foundation

/// Read-only playback state port. Both requirements are called from
/// `Diagnostics.swift`, a file outside the conforming adapter, so neither can
/// register as a dead protocol requirement (a conformance's own implementation
/// line does not count as a reference).
public protocol PlaybackStatePort: Sendable {
    var isPlaying: Bool { get }
    func elapsedSeconds(at date: Date) -> Double
}
