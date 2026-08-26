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
    "a correct credential should authenticate, however many authenticators are chained after it"
)
check(
    authenticateChain([alpha], credential: "wrong-guess") == .rejected(challenges: [alpha.challenge]),
    "a single-authenticator rejection should carry that authenticator's own challenge"
)
check(
    authenticateChain([alpha, beta], credential: "wrong-guess")
        == .rejected(challenges: [alpha.challenge, beta.challenge]),
    "a chained rejection should carry every tried authenticator's challenge, in order"
)

print("OK: main.swift")
