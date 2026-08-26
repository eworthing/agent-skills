// credential_authenticator's own bundled test suite.
//
// Run: swiftc credential_authenticator.swift main.swift -o /tmp/<name> && /tmp/<name>
// Exits 0 on success, 1 on failure.

import Foundation

func check(_ condition: Bool, _ message: String) {
    if !condition {
        print("FAIL: \(message)")
        exit(1)
    }
}

let authenticator = Authenticator(storedPasswords: ["kiosk": "", "morgan": "hunter2"])

check(
    authenticator.authenticate(.some(Credential(username: "morgan", password: "hunter2"))) == "morgan",
    "the correct password for an ordinary account should authenticate"
)
check(
    authenticator.authenticate(.some(Credential(username: "morgan", password: "wrong"))) == nil,
    "a wrong password for an ordinary account should not authenticate"
)
check(
    authenticator.authenticate(.none) == nil,
    "a request carrying no credential at all should never authenticate"
)
check(
    authenticator.authenticate(.some(Credential(username: "kiosk", password: ""))) == "kiosk",
    "kiosk's stored password matches an empty supplied password"
)
check(
    authenticator.authenticate(.some(Credential(username: "kiosk", password: "guess"))) == nil,
    "a non-empty guess for kiosk does not match its stored password"
)

print("OK: main.swift")
