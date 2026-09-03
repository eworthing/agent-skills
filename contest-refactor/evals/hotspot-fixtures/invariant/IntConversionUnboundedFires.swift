func formatTimeMMSS(seconds: Double) -> String {
    guard seconds.isFinite else { return "--:--" }
    let totalSeconds = Int(seconds)
    let minutes = totalSeconds / 60
    let secs = totalSeconds % 60
    return "\(minutes):\(secs < 10 ? "0" : "")\(secs)"
}
