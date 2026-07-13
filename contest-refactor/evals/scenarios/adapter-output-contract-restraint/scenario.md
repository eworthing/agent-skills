# Loop 14 - `data_flow` dimension

**Actor report (`loop_result`):** *"Consolidated the three `updateState` call sites in `RemoteAudioPreviewAdapter` to build `PreviewState` the same way, threading the item duration through each. Less duplication, full suite green (731 tests). Proposing `data_flow` -> 9.5."*

**Test run:** `swift test` - 731 passed, 0 failed.

## Context

`PreviewState` is the application Interface the adapter publishes. Downstream progress UI reads `durationSeconds` and `currentTimeSeconds` to render a progress bar. The remote item's duration is available from `item.duration.seconds`.

## Resulting source

```swift
struct PreviewState {
    let currentTimeSeconds: Double
    let durationSeconds: Double
}

final class RemoteAudioPreviewAdapter {
    private let continuation: AsyncStream<PreviewState>.Continuation
    private var item: RemoteItem?

    private func publish(currentTime: Double) {
        continuation.yield(PreviewState(
            currentTimeSeconds: currentTime,
            durationSeconds: item?.duration.seconds ?? 0
        ))
    }

    func start(_ item: RemoteItem) {
        self.item = item
        publish(currentTime: 0)
    }

    func loopBack() { publish(currentTime: 0) }

    func advance(to time: Double) { publish(currentTime: time) }
}
```

`RemoteAudioPreviewAdapterTests.testPublishesDuration` asserts every emitted `PreviewState` after `start` carries the item's non-zero `durationSeconds`.
