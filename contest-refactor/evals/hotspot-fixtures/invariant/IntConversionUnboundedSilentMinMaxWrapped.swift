func formatTimeMMSS(seconds: Double) -> String {
    // Real shape from BenchHypeKit's post-fix TimeFormatting.swift: the clamp
    // lands in a local via a ternary whose RHS only STARTS with the param.
    // A too-loose alias regex once treated `clamped` as a direct alias of
    // `seconds` and fired anyway -- this pins the fix.
    let clamped = seconds.isFinite ? min(max(seconds, 0), 1e15) : 0
    let totalSeconds = Int(clamped)
    let minutes = totalSeconds / 60
    let secs = totalSeconds % 60
    return "\(minutes):\(secs < 10 ? "0" : "")\(secs)"
}
