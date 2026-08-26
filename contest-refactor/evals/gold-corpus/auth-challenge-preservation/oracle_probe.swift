// Grader-only probe. Not shown to a candidate (listed in provenance.json's
// grader_only_files). Compiled by oracles.py against each variant's own
// challenge_chain.swift in turn (copied to a scratch file literally named
// main.swift -- swiftc only allows top-level statements in a file with
// that exact name -- never the variant's own main.swift).
//
// Usage: probe <single|chain|success>
//   single  -- one authenticator ("alpha"), wrong credential.
//   chain   -- two authenticators ("alpha" then "beta"), wrong credential.
//   success -- two authenticators, alpha's own correct credential.
//
// Prints:
//   authenticated:<identity>              -- on success
//   rejected:<n>                          -- on rejection, n = challenge count
//   <scheme>|<parameter>                  -- one per line, per rejected challenge

import Foundation

let args = CommandLine.arguments
guard args.count == 2 else {
    print("usage: probe <single|chain|success>")
    exit(2)
}
let mode = args[1]

let alpha = Authenticator(scheme: "alpha", parameter: "realm=vault-a") { credential in
    credential == "alpha-secret" ? "alpha-user" : nil
}
let beta = Authenticator(scheme: "beta", parameter: "realm=vault-b") { credential in
    credential == "beta-secret" ? "beta-user" : nil
}

let outcome: AuthOutcome
switch mode {
case "single":
    outcome = authenticateChain([alpha], credential: "wrong-guess")
case "chain":
    outcome = authenticateChain([alpha, beta], credential: "wrong-guess")
case "success":
    outcome = authenticateChain([alpha, beta], credential: "alpha-secret")
default:
    print("bad mode: \(mode)")
    exit(2)
}

switch outcome {
case .authenticated(let identity):
    print("authenticated:\(identity)")
case .rejected(let challenges):
    print("rejected:\(challenges.count)")
    for c in challenges {
        print("\(c.scheme)|\(c.parameter)")
    }
}
