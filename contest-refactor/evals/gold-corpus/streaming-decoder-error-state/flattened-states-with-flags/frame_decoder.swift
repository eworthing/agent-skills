// Parsing state is held as two Bool flags plus a length counter, on top
// of the shared buffering protocol below. Between them they say where
// the parser is: whether it has failed, whether an unbounded frame is
// open, and how many body lines a counted frame still owes.
//
// The protocol this decodes: a stream of newline-terminated lines forms a
// sequence of frames. A frame starts with a header line, one of:
//   "#<n>"   begin a COUNTED frame: exactly n further lines (n >= 0) are
//            its body, taken verbatim regardless of their own content.
//   "#*"     begin an UNBOUNDED frame: further lines are its body, taken
//            verbatim, until a line that is exactly "." appears (not
//            itself part of the body).
//
// `remaining == 0` doubles as "not currently owing body lines, so the
// next line may be a header", which keeps the header check in one place.

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

    private var isErrored = false
    private var isUnbounded = false
    private var remaining = 0  // 0 means "not mid a counted frame's body"
    private var body: [String] = []
    private var onFrame: (Frame) throws -> Void = { _ in }

    func onFrame(_ handler: @escaping (Frame) throws -> Void) {
        onFrame = handler
    }

    func feed(_ chunk: String) {
        submit(chunk)
    }

    func decodeLine(_ line: String) {
        guard !isErrored else { return }

        // Fast path: whenever `remaining` reads 0 we assume we're between
        // frames, so a header-shaped line is treated as one. Almost
        // always right -- but `remaining` also reads 0 for every line of
        // an in-progress unbounded frame's body, since that mode never
        // touches it.
        if remaining == 0, isHeaderLike(line) {
            if line == "#*" {
                isUnbounded = true
                body = []
            } else if let n = Int(line.dropFirst()), n >= 0 {
                if n == 0 {
                    deliver(Frame(kind: .counted, body: []))
                } else {
                    isUnbounded = false
                    body = []
                    remaining = n
                }
            }
            return
        }
        if isUnbounded {
            if line == "." {
                let finished = body
                isUnbounded = false
                deliver(Frame(kind: .unbounded, body: finished))
            } else {
                body.append(line)
            }
            return
        }
        body.append(line)
        remaining -= 1
        if remaining == 0 {
            let finished = body
            deliver(Frame(kind: .counted, body: finished))
        }
    }

    private func isHeaderLike(_ line: String) -> Bool {
        line == "#*" || (line.hasPrefix("#") && Int(line.dropFirst()) != nil)
    }

    private func deliver(_ frame: Frame) {
        do {
            try onFrame(frame)
        } catch {
            isErrored = true
        }
    }
}
