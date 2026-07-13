# Loop 3 - `state_management` dimension

**Actor report (`loop_result`):** *"Renamed `catalogID` to `currentCatalogID` across `AppleMusicPreviewAdapter` for clarity and moved its assignments next to the session-token bookkeeping so the active-catalog state reads in one place. No behavior change, full suite green (884 tests). Proposing `state_management` -> 9.5."*

**Test run:** `swift test` - 884 passed, 0 failed.

## Context

`AppleMusicPreviewAdapter` plays catalog previews. It owns the session token and publishes playback status through `statusContinuation`.

## Resulting source (full type after the change)

```swift
final class AppleMusicPreviewAdapter: PreviewAdapter {
    private let player: MusicPlayer
    private let statusContinuation: AsyncStream<PreviewStatus>.Continuation
    private var sessionToken: SessionToken?
    private var currentCatalogID: CatalogID?

    var status: AsyncStream<PreviewStatus> { statusStream }

    func start(_ item: CatalogItem) async throws {
        sessionToken = try await player.acquireSession()
        currentCatalogID = item.catalogID
        try await player.play(item.catalogID, token: sessionToken)
        statusContinuation.yield(.playing(item.catalogID))
    }

    func stop() {
        player.stop(token: sessionToken)
        sessionToken = nil
        currentCatalogID = nil
        statusContinuation.yield(.stopped)
    }

    func ownershipLost() {
        sessionToken = nil
        currentCatalogID = nil
        statusContinuation.yield(.interrupted)
    }
}
```

`sessionToken` is passed to every `player` call. `AppleMusicPreviewAdapterTests` exercise start/stop/ownership-lost and assert the yielded `PreviewStatus` values.
