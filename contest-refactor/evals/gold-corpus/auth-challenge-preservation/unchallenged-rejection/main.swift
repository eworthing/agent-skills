// challenge_chain's own bundled test suite.
//
// Run: swiftc challenge_chain.swift main.swift -o /tmp/<name> && /tmp/<name>
// Exits 0 on success, 1 on failure.

import Foundation

func check(_ condition: Bool, _ message: String) {
    if !condition {
        print("FAIL: \(message)")
        exit(1)
    }
}

let alpha = Authenticator(scheme: "alpha", parameter: "realm=vault-a") { credential in
    credential == "alpha-secret" ? "alpha-user" : nil
}

check(
    authenticateChain([alpha], credential: "alpha-secret") == .authenticated("alpha-user"),
    "a correct credential should authenticate"
)
check(
    authenticateChain([alpha], credential: "wrong-guess") == .rejected(challenges: []),
    "a wrong credential should be rejected"
)

print("OK: main.swift")
