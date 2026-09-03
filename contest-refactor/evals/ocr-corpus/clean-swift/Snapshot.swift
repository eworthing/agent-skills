import Foundation

/// Persisted snapshot of a trim span and gain. Decoding delegates to the
/// throwing initializer, so a corrupt payload can never bypass `TrimSpan`'s
/// invariants -- the `codable_bypasses_throwing_init` signal must never fire
/// here.
public struct Snapshot: Codable, Hashable, Sendable {
    public let span: TrimSpan
    public let gain: GainLevel

    public init(span: TrimSpan, gain: GainLevel) {
        self.span = span
        self.gain = gain
    }

    private enum CodingKeys: String, CodingKey {
        case startSeconds
        case endSeconds
        case gain
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let start = try container.decode(Double.self, forKey: .startSeconds)
        let end = try container.decode(Double.self, forKey: .endSeconds)
        let rawGain = try container.decode(Double.self, forKey: .gain)
        self.span = try TrimSpan(startSeconds: start, endSeconds: end)
        self.gain = GainLevel(rawValue: rawGain)
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(span.startSeconds, forKey: .startSeconds)
        try container.encode(span.endSeconds, forKey: .endSeconds)
        try container.encode(gain.rawValue, forKey: .gain)
    }
}
