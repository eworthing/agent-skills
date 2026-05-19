# Speech Recognition + MusicKit Coexistence

When an iOS app uses both the Speech framework (`SFSpeechRecognizer` +
`AVAudioEngine` recording tap) and MusicKit playback in the same flow —
e.g. "speak a request → parse it → build a playlist → play it" — two
distinct AVFoundation crashes appear:

1. `required condition is false: nullptr == Tap()` (a hard crash from `AVAEGraphNode.mm:828:CreateRecordingTap`)
2. `applicationQueuePlayer _establishConnectionIfNeeded timeout [ping did not pong]` (a soft hang followed by `MPMusicPlayerControllerErrorDomain` error 1)

Both come from AVFoundation, not MusicKit. The fix is in audio-session
discipline.

## Contents

- [Why each crash happens](#why-each-crash-happens)
- [Required pattern: removeTap before installTap](#required-pattern-removetap-before-installtap)
- [Required pattern: full stopRecording before MusicKit](#required-pattern-full-stoprecording-before-musickit)
- [`isRecording` guard](#isrecording-guard)
- [Single-flow rule](#single-flow-rule)
- [Code skeleton](#code-skeleton)

## Why each crash happens

**`nullptr == Tap()`** — `AVAudioEngine.inputNode` permits exactly one
recording tap at a time. If `installTap(onBus: 0, ...)` is called when a
tap is already installed (because a previous `startRecording()` did not
pair with `removeTap`, or because `startRecording()` was called twice in
a row), AVFoundation throws an uncaught exception and the app
terminates. The fix is to make every install idempotent: call
`removeTap(onBus: 0)` first, unconditionally.

**`applicationQueuePlayer ... timeout`** — `ApplicationMusicPlayer`
brokers a connection to a queue daemon. If the app's audio session is
contested — typically because a Speech recording tap is still active and
holding the input node — the connection ping/pong times out. The next
`player.play()` returns `MPMusicPlayerControllerErrorDomain` error 1.
The fix is to fully tear down speech (engine stop, tap remove, request
end) before any MusicKit playback call.

These two failures are coupled. Apps that hit the timeout almost always
also hit the tap crash on the next user interaction; both come from the
same root cause: speech and playback being live simultaneously.

## Required pattern: removeTap before installTap

Make every `installTap` idempotent. Always remove first:

```swift
// In startRecording(), before installing a new tap:
audioEngine.inputNode.removeTap(onBus: 0)   // no-op if none installed
audioEngine.inputNode.installTap(onBus: 0, bufferSize: 1024, format: format) { buffer, _ in
    request.append(buffer)
}
```

`removeTap(onBus:)` is safe to call when no tap is installed; it is a
no-op in that case. Calling it before every `installTap` costs nothing
and prevents the `nullptr == Tap()` crash entirely.

## Required pattern: full stopRecording before MusicKit

`stopRecording()` (or whatever you call your cleanup) must include all
three of these calls, in this order, before any MusicKit call runs:

```swift
func stopRecording() {
    audioEngine.stop()
    audioEngine.inputNode.removeTap(onBus: 0)
    recognitionRequest?.endAudio()
    recognitionRequest = nil
    recognitionTask?.cancel()
    recognitionTask = nil
    isRecording = false
}
```

Omitting any of these leaves the audio session held by Speech. The next
`MusicCatalogSearchRequest.response()` may succeed (search is HTTP, not
audio-bound), but `ApplicationMusicPlayer.shared.play()` will time out.

## `isRecording` guard

Track recording state explicitly. Do not derive it from
`audioEngine.isRunning` alone, because the engine can be running for
playback even when no tap is installed.

```swift
@MainActor
@Observable
final class SpeechCoordinator {
    private(set) var isRecording = false

    func startRecording() throws {
        guard !isRecording else { return }       // already on
        audioEngine.inputNode.removeTap(onBus: 0)
        audioEngine.inputNode.installTap(...) { ... }
        try audioEngine.start()
        isRecording = true
    }

    func stopRecording() {
        guard isRecording else { return }
        audioEngine.stop()
        audioEngine.inputNode.removeTap(onBus: 0)
        recognitionRequest?.endAudio()
        isRecording = false
    }
}
```

The guard prevents double-start (`installTap` twice) and double-stop
(`removeTap` is safe, but calling `recognitionRequest?.endAudio()` twice
can race against the recognition task's own teardown).

## Single-flow rule

Pick one mode per user interaction:

- **(a) Voice flow:** user holds-to-speak → release → `stopRecording()` (full teardown, as above) → `MusicCatalogSearchRequest` → `ApplicationMusicPlayer.shared.play()`. Speech and playback are sequential; the recording tap is gone before playback starts.
- **(b) Text flow:** user types in a `TextField` → `MusicCatalogSearchRequest` → playback. No speech recognizer involved.

Never run speech and playback simultaneously. Specifically: do not
install a recording tap while `ApplicationMusicPlayer` is in a
connecting or playing state, and do not start playback while a recording
tap is installed. The audio session can only meaningfully serve one of
those at a time, and the failure mode is the timeout described above.

If your UI offers a "press to talk while music plays" affordance,
implement it by pausing playback first, then starting recording — and
reverse on release. Do not try to overlap them.

## Code skeleton

A correct sequence for a voice → playlist flow:

```swift
@MainActor
func handleVoiceTranscript(_ transcript: String) async {
    // 1. Make sure speech is fully torn down before touching MusicKit.
    speechCoordinator.stopRecording()    // no-op if already stopped

    // 2. Confirm authorization (MusicAuthorization.request() should
    //    have run on screen appear; check the cached flag here).
    guard isAuthorized else {
        statusMessage = "Authorize Apple Music first."
        return
    }

    // 3. Search catalog (HTTP — safe even if audio session is contested,
    //    but we've already cleaned it up).
    var request = MusicCatalogSearchRequest(term: transcript, types: [Song.self])
    request.limit = 25

    do {
        let response = try await request.response()
        let songs = Array(response.songs)

        // 4. Start playback. By now: no recording tap, audio session
        //    available, MusicAuthorization == .authorized.
        ApplicationMusicPlayer.shared.queue = .init(for: songs)
        try await ApplicationMusicPlayer.shared.play()
    } catch {
        // See error-codes.md for the diagnostic injection pattern.
        let ns = error as NSError
        statusMessage = "Search/playback failed: \(ns.domain) \(ns.code)"
    }
}
```

If you also save to the library in this flow (`MusicLibrary.shared.createPlaylist` + `add`), put that step **before** the playback call. See `library-playlists.md`.
