// error_detail's own bundled test suite.
//
// Run: swiftc error_detail.swift main.swift -o /tmp/<name> && /tmp/<name>
// Exits 0 on success, 1 on failure.

import Foundation

func check(_ condition: Bool, _ message: String) {
    if !condition {
        print("FAIL: \(message)")
        exit(1)
    }
}

do {
    let result = try withErrorMiddleware { "ok" }
    check(result == "ok", "an operation that does not fail should pass its result through untouched")
} catch {
    check(false, "an operation that does not fail should not raise anything")
}

let original = rejectMissingCredential()
do {
    _ = try withErrorMiddleware { throw original }
    check(false, "a failing operation should raise an error through the middleware")
} catch let detail as RethrownDetail {
    check(detail.recoveredReason == original.reason, "the reason should survive the middleware")
    check(detail.recoveredChallenge == original.challenge, "the challenge should survive the middleware")
    check(detail.recoveredIdentifier != nil, "an identifier should be attached")
    check(detail.recoveredSource == original.source, "the source location should survive the middleware")
} catch {
    check(false, "the rethrown error should still carry recoverable detail")
}

print("OK: main.swift")
