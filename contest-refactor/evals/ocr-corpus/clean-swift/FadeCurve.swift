import Foundation

/// Fade-in/out envelope over a `TrimSpan`. Both members are checked in both
/// directions and for finiteness before the span comparison runs.
public struct FadeCurve: Hashable, Sendable {
    public let fadeInSeconds: Double
    public let fadeOutSeconds: Double

    public init(fadeInSeconds: Double, fadeOutSeconds: Double, over span: TrimSpan) throws {
        guard fadeInSeconds.isFinite, fadeInSeconds >= 0 else {
            throw FadeCurveError.invalidFadeIn
        }
        guard fadeOutSeconds.isFinite, fadeOutSeconds >= 0 else {
            throw FadeCurveError.invalidFadeOut
        }
        guard fadeInSeconds + fadeOutSeconds <= span.durationSeconds else {
            throw FadeCurveError.fadeExceedsSpan
        }
        self.fadeInSeconds = fadeInSeconds
        self.fadeOutSeconds = fadeOutSeconds
    }
}

public enum FadeCurveError: Error, Hashable, Sendable {
    case invalidFadeIn
    case invalidFadeOut
    case fadeExceedsSpan
}
