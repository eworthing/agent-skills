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

    // Decoding routes through the throwing init, so `codable_bypasses_throwing_init`
    // must stay silent here.
    private enum CodingKeys: String, CodingKey {
        case startSeconds
        case endSeconds
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        try self.init(
            startSeconds: container.decode(Double.self, forKey: .startSeconds),
            endSeconds: container.decode(Double.self, forKey: .endSeconds),
        )
    }
}

public enum TrimSpanError: Error, Hashable, Sendable {
    case invalidStart
    case invalidEnd
}
