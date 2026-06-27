import AVFoundation

/// Configures the app's AVAudioSession for playback and recording.
/// Calls AVAudioSession directly — no Seam at the hardware-bound API boundary.
final class AudioSessionManager {

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
