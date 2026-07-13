import Foundation

/// Application-lifetime event bus. Created once at the composition root and kept
/// for the life of the process; subscriptions are never removed.
final class EventHub {
    private var subscribers: [String: [(String) -> Void]] = [:]

    /// Registers `handler` for `event`. Handlers stay registered for the hub's lifetime.
    func subscribe(_ event: String, handler: @escaping (String) -> Void) {
        subscribers[event, default: []].append(handler)
    }

    /// Delivers `payload` to every handler registered for `event`.
    func publish(_ event: String, payload: String) {
        for handler in subscribers[event] ?? [] {
            handler(payload)
        }
    }
}

/// Processes one capture session's frames and reports stage activity.
final class ImagePipeline {
    let stageName: String
    /// Raw working set for the session; sized in the tens of megabytes in production.
    private(set) var frameBuffer: [UInt8]
    private(set) var log: [String] = []

    init(stageName: String, frameBuffer: [UInt8], hub: EventHub) {
        self.stageName = stageName
        self.frameBuffer = frameBuffer
        hub.subscribe("flush") { payload in
            self.log.append("\(self.stageName) flushed: \(payload)")
        }
    }

    /// Trims the working set to `size` frames and reports the new count. The
    /// completion closure runs once, immediately, and is not stored anywhere.
    func cropFrames(to size: Int, completion: (Int) -> Void) {
        frameBuffer = Array(frameBuffer.prefix(size))
        completion(frameBuffer.count)
    }
}
