import Foundation

// A hit counter shared between two call sites: page-view recording and
// API-hit recording. A lock serializes every access to `count`.

final class HitCounter: Sendable {
    private let lock = NSLock()
    private nonisolated(unsafe) var count = 0

    func increment() {
        lock.lock()
        defer { lock.unlock() }
        count += 1
    }

    var currentCount: Int {
        lock.lock()
        defer { lock.unlock() }
        return count
    }

    func statusLine() -> String {
        "hits recorded: \(currentCount)"
    }
}

func recordPageView(_ counter: HitCounter) {
    counter.increment()
}

func recordAPIHit(_ counter: HitCounter) {
    counter.increment()
}
