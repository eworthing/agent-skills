// A minimal outbound pipe: values are written, then flushed out once the
// pipe is live. Nothing is live until `activate()` is called.

final class Pipe {
    private(set) var isLive = false
    private var buffered: [Int] = []
    private(set) var emitted: [Int] = []

    /// Accepts `value` for later delivery. Returns false, rejecting the
    /// write outright, if this pipe is not yet live -- there is nothing
    /// live to send to yet.
    @discardableResult
    func write(_ value: Int) -> Bool {
        guard isLive else {
            return false
        }
        buffered.append(value)
        return true
    }

    func flush() {
        emitted.append(contentsOf: buffered)
        buffered.removeAll()
    }

    func activate() {
        isLive = true
    }
}
