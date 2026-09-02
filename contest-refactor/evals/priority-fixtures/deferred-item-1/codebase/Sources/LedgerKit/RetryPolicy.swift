import Foundation

/// Bounded retry with exponential backoff for the confirmations upload.
public struct RetryPolicy {
    public let maxAttempts: Int
    public let baseDelay: TimeInterval

    public init(maxAttempts: Int = 4, baseDelay: TimeInterval = 0.5) {
        self.maxAttempts = maxAttempts
        self.baseDelay = baseDelay
    }

    public func delay(forAttempt attempt: Int) -> TimeInterval {
        var delay = baseDelay
        var remaining = attempt
        while remaining > 1 {
            delay *= 2
            remaining -= 1
        }
        return delay
    }

    public func shouldRetry(attempt: Int, error: Error) -> Bool {
        if attempt >= maxAttempts { return false }
        let ns = error as NSError
        if ns.domain == NSURLErrorDomain {
            return ns.code == NSURLErrorTimedOut || ns.code == NSURLErrorNetworkConnectionLost
        }
        return false
    }
}
