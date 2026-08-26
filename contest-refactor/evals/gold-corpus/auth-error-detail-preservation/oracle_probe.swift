// Grader-only probe. Not shown to a candidate (listed in provenance.json's
// grader_only_files). Compiled by oracles.py against each variant's own
// error_detail.swift in turn (copied to a scratch file literally named
// main.swift -- swiftc only allows top-level statements in a file with
// that exact name -- never the variant's own main.swift).
//
// Usage: probe <fail|succeed>
//   fail    -- the guarded operation raises rejectMissingCredential()
//              through withErrorMiddleware; prints what a caller downstream
//              of the middleware actually recovers, field by field.
//   succeed -- the guarded operation returns normally; prints the result.
//
// Prints (fail mode), one field per line, "MISSING" for an absent one:
//   reason:<value|MISSING>
//   challenge:<value|MISSING>
//   identifier:<value|MISSING>
//   source:<value|MISSING>
// Prints (succeed mode):
//   result:<value>

import Foundation

let args = CommandLine.arguments
guard args.count == 2, args[1] == "fail" || args[1] == "succeed" else {
    print("usage: probe <fail|succeed>")
    exit(2)
}
let mode = args[1]

func guardedOperation() throws -> String {
    if mode == "fail" {
        throw rejectMissingCredential()
    }
    return "ok"
}

do {
    let result = try withErrorMiddleware(guardedOperation)
    print("result:\(result)")
} catch let detail as RethrownDetail {
    print("reason:\(detail.recoveredReason ?? "MISSING")")
    print("challenge:\(detail.recoveredChallenge ?? "MISSING")")
    print("identifier:\(detail.recoveredIdentifier ?? "MISSING")")
    print("source:\(detail.recoveredSource?.description ?? "MISSING")")
} catch {
    print("reason:MISSING")
    print("challenge:MISSING")
    print("identifier:MISSING")
    print("source:MISSING")
}
