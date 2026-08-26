// A hit counter shared between two call sites: page-view recording and
// API-hit recording.

final class HitCounter: Sendable {
    // Only mutated during setup, before either call site can reach it.
    nonisolated(unsafe) var count = 0

    func setup(initial: Int) {
        count = initial
    }

    func increment() {
        count += 1
    }

    var currentCount: Int {
        count
    }

    func statusLine() -> String {
        "hits recorded: \(count)"
    }
}

func recordPageView(_ counter: HitCounter) {
    counter.increment()
}

func recordAPIHit(_ counter: HitCounter) {
    counter.increment()
}
