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

do {
    _ = try withErrorMiddleware { throw rejectMissingCredential() }
    check(false, "a failing operation should raise an error through the middleware")
} catch let detail as RethrownDetail {
    check(false, "did not expect a recoverable detail, but got \(detail)")
} catch {
    // A failing operation raises here; no recoverable detail is expected.
}

print("OK: main.swift")
