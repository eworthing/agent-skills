// The "before": a decoder that hand-rolls its own line-buffering,
// re-entrancy guarding, and leftover-bytes bookkeeping directly inside the
// same type that also owns parsing state. There is no reusable buffering
// layer here -- every parser that wants line-at-a-time delivery over
// arbitrarily-chunked input has to reimplement this same bookkeeping for
// itself, tangled with whatever that parser's own states are.
//
// The protocol this decodes: a stream of newline-terminated lines forms a
// sequence of frames. A frame starts with a header line, one of:
//   "#<n>"   begin a COUNTED frame: exactly n further lines (n >= 0) are
//            its body, taken verbatim regardless of their own content.
//   "#*"     begin an UNBOUNDED frame: further lines are its body, taken
//            verbatim, until a line that is exactly "." appears (not
//            itself part of the body).
// A line's meaning is decided entirely by which of these states the
// decoder is currently in -- never by sniffing what the line looks like
// once a frame is already open.

enum FrameKind: String {
    case counted
    case unbounded
}

struct Frame: Equatable, CustomStringConvertible {
    let kind: FrameKind
    let body: [String]

    var description: String {
        "\(kind.rawValue):[\(body.joined(separator: "|"))]"
    }
}

enum DecodeConsumerError: Error {
    case rejected
}

final class FrameDecoder {
    // Buffering, re-entrancy guarding, and leftover-bytes bookkeeping,
    // duplicated here rather than shared, because this decoder predates
    // any common driver for it.
    private var pending: String = ""
    private var queuedLines: [String] = []
    private var isDecoding = false

    private var state: State = .awaitingHeader
    private var body: [String] = []
    private var onFrame: (Frame) throws -> Void = { _ in }

    private enum State {
        case awaitingHeader
        case awaitingCountedContinuation(remaining: Int)
        case awaitingUnboundedContinuation
    }

    func onFrame(_ handler: @escaping (Frame) throws -> Void) {
        onFrame = handler
    }

    func feed(_ chunk: String) {
        pending += chunk
        while let newlineIndex = pending.firstIndex(of: "\n") {
            let line = String(pending[pending.startIndex..<newlineIndex])
            pending.removeSubrange(pending.startIndex...newlineIndex)
            queuedLines.append(line)
        }
        // Re-entrancy guard: a consumer callback invoked from decodeLine
        // below can itself call feed() again (for example, if it reacts
        // to a frame by pushing more input). Without this guard, that
        // nested call would recurse into the drain loop while the outer
        // call is still mutating `queuedLines`.
        guard !isDecoding else { return }
        isDecoding = true
        while !queuedLines.isEmpty {
            let next = queuedLines.removeFirst()
            decodeLine(next)
        }
        isDecoding = false
    }

    private func decodeLine(_ line: String) {
        switch state {
        case .awaitingHeader:
            if line == "#*" {
                body = []
                state = .awaitingUnboundedContinuation
            } else if line.hasPrefix("#"), let n = Int(line.dropFirst()), n >= 0 {
                if n == 0 {
                    deliver(Frame(kind: .counted, body: []))
                } else {
                    body = []
                    state = .awaitingCountedContinuation(remaining: n)
                }
            }
            // Anything else while awaiting a header is not a recognized
            // frame start; this fixture has no oracle exercising that
            // path, so it is a silent no-op rather than a designed error
            // path.
        case .awaitingCountedContinuation(let remaining):
            body.append(line)
            let left = remaining - 1
            if left == 0 {
                let finished = body
                state = .awaitingHeader
                deliver(Frame(kind: .counted, body: finished))
            } else {
                state = .awaitingCountedContinuation(remaining: left)
            }
        case .awaitingUnboundedContinuation:
            if line == "." {
                let finished = body
                state = .awaitingHeader
                deliver(Frame(kind: .unbounded, body: finished))
            } else {
                body.append(line)
            }
        }
    }

    private func deliver(_ frame: Frame) {
        // No error-latch here: if the consumer throws, this predates that
        // safeguard entirely -- the error is swallowed and decoding
        // continues exactly as if nothing happened. That is the specific
        // gap a later change (kept out of this variant on purpose) closes.
        try? onFrame(frame)
    }
}
