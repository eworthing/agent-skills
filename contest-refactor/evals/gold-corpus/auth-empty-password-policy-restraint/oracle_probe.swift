// Grader-only probe. Not shown to a candidate (listed in provenance.json's
// grader_only_files). Compiled by oracles.py against each variant's own
// credential_authenticator.swift in turn (never against main.swift -- two
// files with top-level statements can't coexist in one swiftc
// invocation), so this is the one place `Authenticator.authenticate` gets
// called uniformly across variants whose internals differ.
//
// Usage:
//   probe none
//   probe some <username> <password>
//
// Both forms use the same fixed account directory (kiosk: "", morgan:
// "hunter2"). Prints the authenticated username, or "nil".

import Foundation

let authenticator = Authenticator(storedPasswords: ["kiosk": "", "morgan": "hunter2"])

let args = CommandLine.arguments
guard args.count >= 2 else {
    print("usage: probe none | probe some <username> <password>")
    exit(2)
}

let supplied: SuppliedCredential
switch args[1] {
case "none":
    supplied = .none
case "some":
    guard args.count == 4 else {
        print("usage: probe some <username> <password>")
        exit(2)
    }
    supplied = .some(Credential(username: args[2], password: args[3]))
default:
    print("unknown mode: \(args[1])")
    exit(2)
}

print(authenticator.authenticate(supplied) ?? "nil")
