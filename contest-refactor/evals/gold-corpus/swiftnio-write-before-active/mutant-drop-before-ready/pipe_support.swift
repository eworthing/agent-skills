// A minimal outbound pipe: values are written, then flushed out once the
// pipe is live. Nothing is live until `activate()` is called.
//
// A write is never rejected: if the pipe isn't live yet, the value is
// held and sent as soon as it can be. Activation itself attempts to send
// anything already waiting, rather than requiring a separate flush
// afterward to notice.

final class Pipe {
    private(set) var isLive = false
    private var buffered: [Int] = []
    private(set) var emitted: [Int] = []

    @discardableResult
    func write(_ value: Int) -> Bool {
        guard isLive else {
            return true
        }
        buffered.append(value)
        return true
    }

    func flush() {
        guard isLive else { return }
        emitted.append(contentsOf: buffered)
        buffered.removeAll()
    }

    func activate() {
        isLive = true
        flush()
    }
}
