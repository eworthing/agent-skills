import Foundation

/// Namespace for time-string formatting. The `Int(_:)` conversion is clamped
/// to `Int`'s representable range *before* conversion, so it can never trap
/// -- the `int_conversion_unbounded` signal must never fire here.
public enum DurationFormatter {
    public static func mmss(_ seconds: Double) -> String {
        let bounded = seconds.isFinite ? min(max(seconds, 0), Double(Int.max)) : 0
        let totalSeconds = bounded >= Double(Int.max) ? Int.max : Int(bounded)
        let minutes = totalSeconds / 60
        let remainder = totalSeconds % 60
        return "\(minutes):\(remainder < 10 ? "0" : "")\(remainder)"
    }
}
