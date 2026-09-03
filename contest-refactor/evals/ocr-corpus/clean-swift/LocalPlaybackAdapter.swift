import Foundation

/// Concrete `PlaybackStatePort` backed by a wall-clock start time.
public struct LocalPlaybackAdapter: PlaybackStatePort {
    public let isPlaying: Bool
    private let startedAt: Date

    public init(isPlaying: Bool, startedAt: Date) {
        self.isPlaying = isPlaying
        self.startedAt = startedAt
    }

    public func elapsedSeconds(at date: Date) -> Double {
        max(0, date.timeIntervalSince(startedAt))
    }
}
