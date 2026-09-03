import Foundation

/// Exercises every declared member of this corpus from a file other than the
/// one that declares it, so the dead-surface aid has no zero-reference
/// candidate to find. Not a real diagnostics feature -- a wiring fixture.
///
/// Top-level (not a type member), deliberately: this is the fixture's own
/// entry point, so nothing in the corpus calls it back, and the dead-surface
/// aid's v1 declaration scope excludes top-level functions for exactly that
/// reason (only type-member declarations are scanned).
public func summarizeDiagnostics(now: Date) throws -> String {
    let span = try TrimSpan(startSeconds: 1, endSeconds: 9)
    let fade = try FadeCurve(fadeInSeconds: 1, fadeOutSeconds: 1, over: span)
    let gain = GainLevel.unity
    let snapshot = Snapshot(span: span, gain: gain)
    let tracks = try TrackSet(trackIDs: [UUID(), UUID()])
    let roster = try RosterList(memberIDs: [UUID(), UUID()])
    let adapter = LocalPlaybackAdapter(isPlaying: true, startedAt: now)

    let trimErrors: [TrimSpanError] = [.invalidStart, .invalidEnd]
    let fadeErrors: [FadeCurveError] = [.invalidFadeIn, .invalidFadeOut, .fadeExceedsSpan]
    let trackError = TrackSetError.duplicateTrackID
    let rosterError = RosterListError.duplicateMemberID

    let parts = [
        DurationFormatter.mmss(span.durationSeconds),
        DurationFormatter.mmss(fade.fadeInSeconds + fade.fadeOutSeconds),
        DurationFormatter.mmss(snapshot.span.endSeconds),
        "\(gain.rawValue)",
        "\(tracks.trackIDs.count)",
        "\(roster.memberIDs.count)",
        "\(adapter.isPlaying)",
        "\(adapter.elapsedSeconds(at: now))",
        "\(trimErrors.count)",
        "\(fadeErrors.count)",
        "\(trackError)",
        "\(rosterError)",
    ]
    return parts.joined(separator: " ")
}
