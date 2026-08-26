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
let beta = Authenticator(scheme: "beta", parameter: "realm=vault-b") { credential in
    credential == "beta-secret" ? "beta-user" : nil
}

check(
    authenticateChain([alpha, beta], credential: "alpha-secret") == .authenticated("alpha-user"),
    "a correct credential should authenticate"
)
if case .rejected(let challenges) = authenticateChain([alpha, beta], credential: "wrong-guess") {
    check(challenges.count == 2, "a chained rejection should carry one challenge per tried authenticator")
} else {
    check(false, "a wrong credential should be rejected, not authenticated")
}

print("OK: main.swift")
