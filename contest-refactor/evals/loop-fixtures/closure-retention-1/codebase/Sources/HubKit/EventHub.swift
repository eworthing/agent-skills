import Foundation

/// Application-lifetime event bus. Created once at the composition root and kept
/// for the life of the process; subscriptions are never removed.
public final class EventHub {
    private var subscribers: [String: [(String) -> Void]] = [:]

    public init() {}

    /// Registers `handler` for `event`. Handlers stay registered for the hub's lifetime.
    public func subscribe(_ event: String, handler: @escaping (String) -> Void) {
        subscribers[event, default: []].append(handler)
    }

    /// Delivers `payload` to every handler registered for `event`.
    public func publish(_ event: String, payload: String) {
        for handler in subscribers[event] ?? [] {
            handler(payload)
        }
    }
}

/// Processes one capture session's frames and reports stage activity.
public final class ImagePipeline {
    public let stageName: String
    /// Raw working set for the session; sized in the tens of megabytes in production.
    public private(set) var frameBuffer: [UInt8]
    public private(set) var log: [String] = []

    public init(stageName: String, frameBuffer: [UInt8], hub: EventHub) {
        self.stageName = stageName
        self.frameBuffer = frameBuffer
        hub.subscribe("flush") { payload in
            self.log.append("\(self.stageName) flushed: \(payload)")
        }
    }

    /// Trims the working set to `size` frames and reports the new count. The
    /// completion closure runs once, immediately, and is not stored anywhere.
    public func cropFrames(to size: Int, completion: (Int) -> Void) {
        frameBuffer = Array(frameBuffer.prefix(size))
        completion(frameBuffer.count)
    }
}
