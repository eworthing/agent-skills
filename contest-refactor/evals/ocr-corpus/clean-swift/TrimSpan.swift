import Foundation

/// Bounded, finite trim span. Every comparison is two-sided and finite-checked,
/// so the invariant queue's `one_sided_guard` signal must never fire here.
public struct TrimSpan: Hashable, Sendable, Codable {
    public let startSeconds: Double
    public let endSeconds: Double

    public init(startSeconds: Double, endSeconds: Double) throws {
        guard startSeconds.isFinite, startSeconds >= 0 else {
            throw TrimSpanError.invalidStart
        }
        guard endSeconds.isFinite, endSeconds > startSeconds else {
            throw TrimSpanError.invalidEnd
        }
        self.startSeconds = startSeconds
        self.endSeconds = endSeconds
    }

    public var durationSeconds: Double {
        endSeconds - startSeconds
    }
}

public enum TrimSpanError: Error, Hashable, Sendable {
    case invalidStart
    case invalidEnd
}
