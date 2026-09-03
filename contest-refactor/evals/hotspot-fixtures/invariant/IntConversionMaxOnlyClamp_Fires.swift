// fid 262 shape (formatTimeMMSS, pre-fix): the local traces back to the
// param through a ternary (`clamped = time.isFinite ? max(time, 0) : 0`),
// and only a floor (`max(`) exists -- no `min(` anywhere on the chain, so
// `Int(_:)` can still trap on a huge finite value. Must fire regardless of
// isFinite being present.
func formatTimeMMSS(seconds: Double) -> String {
    let clamped = seconds.isFinite ? max(seconds, 0) : 0
    let totalSeconds = Int(clamped)
    let minutes = totalSeconds / 60
    let secs = totalSeconds % 60
    return "\(minutes):\(secs < 10 ? "0" : "")\(secs)"
}
