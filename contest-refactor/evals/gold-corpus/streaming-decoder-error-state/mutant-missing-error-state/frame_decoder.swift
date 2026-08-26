// Buffering and re-entrancy guarding are factored out into a small
// shared protocol (below); the parser keeps its own multi-state machine.
// A consumer that throws for one frame does not stop the stream: the
// decoder carries on with the lines that follow.
//
// The protocol this decodes: a stream of newline-terminated lines forms a
// sequence of frames. A frame starts with a header line, one of:
//   "#<n>"   begin a COUNTED frame: exactly n further lines (n >= 0) are
//            its body, taken verbatim regardless of their own content.
//   "#*"     begin an UNBOUNDED frame: further lines are its body, taken
//            verbatim, until a line that is exactly "." appears (not
//            itself part of the body).
// A line's meaning is decided entirely by which state the decoder is
// currently in -- never by sniffing what the line looks like once a frame
// is already open.

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

protocol IncrementalLineDecoder: AnyObject {
    var pendingText: String { get set }
    var queuedLines: [String] { get set }
    var isDecoding: Bool { get set }
    func decodeLine(_ line: String)
}

extension IncrementalLineDecoder {
    func submit(_ chunk: String) {
        pendingText += chunk
        while let newlineIndex = pendingText.firstIndex(of: "\n") {
            let line = String(pendingText[pendingText.startIndex..<newlineIndex])
            pendingText.removeSubrange(pendingText.startIndex...newlineIndex)
            queuedLines.append(line)
        }
        drainQueue()
    }

    private func drainQueue() {
        guard !isDecoding else { return }
        isDecoding = true
        while !queuedLines.isEmpty {
            let next = queuedLines.removeFirst()
            decodeLine(next)
        }
        isDecoding = false
    }
}

final class FrameDecoder: IncrementalLineDecoder {
    var pendingText: String = ""
    var queuedLines: [String] = []
    var isDecoding: Bool = false

    private var state: State = .awaitingHeader
    private var body: [String] = []
    private var onFrame: (Frame) throws -> Void = { _ in }

    enum State {
        case awaitingHeader
        case awaitingCountedContinuation(remaining: Int)
        case awaitingUnboundedContinuation
        // No `.errored` case -- the shared-protocol move landed, but the
        // error-latch never came with it.
    }

    func onFrame(_ handler: @escaping (Frame) throws -> Void) {
        onFrame = handler
    }

    func feed(_ chunk: String) {
        submit(chunk)
    }

    func decodeLine(_ line: String) {
        switch state {
        case .awaitingHeader:
            if line == "#*" {
                body = []
                state = .awaitingUnboundedContinuation
            } else if line.hasPrefix("#"), let n = Int(line.dropFirst()), n >= 0 {
                if n == 0 {
                    emit(Frame(kind: .counted, body: []))
                } else {
                    body = []
                    state = .awaitingCountedContinuation(remaining: n)
                }
            }
        case .awaitingCountedContinuation(let remaining):
            body.append(line)
            let left = remaining - 1
            if left == 0 {
                let finished = body
                state = .awaitingHeader
                emit(Frame(kind: .counted, body: finished))
            } else {
                state = .awaitingCountedContinuation(remaining: left)
            }
        case .awaitingUnboundedContinuation:
            if line == "." {
                let finished = body
                state = .awaitingHeader
                emit(Frame(kind: .unbounded, body: finished))
            } else {
                body.append(line)
            }
        }
    }

    private func emit(_ frame: Frame) {
        // The removed contribution: no do/catch, no latch. A throw here
        // is swallowed and the state machine proceeds exactly as if the
        // consumer had succeeded.
        try? onFrame(frame)
    }
}
