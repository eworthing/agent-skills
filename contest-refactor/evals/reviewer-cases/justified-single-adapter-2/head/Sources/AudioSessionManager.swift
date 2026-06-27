import AVFoundation

// MARK: — Seam (Unified Seam Policy b(iii))
//
// (iii) Platform-isolation: AVAudioSession is hardware-bound with no test harness.
//       setCategory(_:mode:) and setActive(_:) require real audio hardware and
//       cannot be reliably reproduced in XCTest on CI. This is the explicit
//       "SDK with no test harness, e.g. Spotify SDK, hardware-bound APIs" carve-out.
//       A single prod adapter is sufficient — no second behavioral adapter required.

/// Controls AVAudioSession category and activation lifecycle.
protocol AudioSessionConfiguring {
    func activateForPlayback() throws
    func activateForRecording() throws
    func deactivate() throws
}

/// Production adapter — delegates to AVAudioSession.sharedInstance().
final class SystemAudioSessionConfigurator: AudioSessionConfiguring {

    func activateForPlayback() throws {
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.playback, mode: .default)
        try session.setActive(true)
    }

    func activateForRecording() throws {
        let session = AVAudioSession.sharedInstance()
        try session.setCategory(.record, mode: .measurement)
        try session.setActive(true)
    }

    func deactivate() throws {
        try AVAudioSession.sharedInstance().setActive(false)
    }
}
