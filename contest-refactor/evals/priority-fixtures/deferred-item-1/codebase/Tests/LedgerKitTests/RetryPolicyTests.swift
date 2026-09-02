import Foundation
import Testing
@testable import LedgerKit

@Test func delayDoublesPerAttempt() {
    let policy = RetryPolicy(maxAttempts: 4, baseDelay: 0.5)
    #expect(policy.delay(forAttempt: 1) == 0.5)
    #expect(policy.delay(forAttempt: 3) == 2.0)
}

@Test func stopsAtMaxAttempts() {
    let policy = RetryPolicy(maxAttempts: 2, baseDelay: 0.1)
    let timeout = NSError(domain: NSURLErrorDomain, code: NSURLErrorTimedOut)
    #expect(policy.shouldRetry(attempt: 2, error: timeout) == false)
}

@Test func nonNetworkErrorsAreNotRetried() {
    let policy = RetryPolicy()
    #expect(policy.shouldRetry(attempt: 1, error: LedgerError.memoTooLong) == false)
}
