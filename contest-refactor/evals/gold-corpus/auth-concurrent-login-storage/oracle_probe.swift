// Grader-only probe. Not shown to a candidate (listed in provenance.json's
// grader_only_files). Compiled by oracles.py against each variant's own
// login_registry.swift in turn (never against main.swift -- two files with
// top-level statements can't coexist in one swiftc invocation), so this is
// the one place a scripted interleaving of two logical callers gets driven
// uniformly across variants whose internals differ.
//
// Usage:
//   probe <token> [<token> ...]
//
// Each token is one of:
//   begin:<slot>:<kindRaw>:<value>   -- calls beginStore for caller <slot>
//                                       ("A" or "B"), remembering the
//                                       returned PendingStore under that
//                                       slot for a later commit
//   commit:<slot>                    -- calls commitStore for whatever
//                                       PendingStore is remembered under
//                                       <slot>
//   retrieve:<kindRaw>                -- calls retrieve(kind:)
//
// One line of output per token, in order: "-" for begin/commit, or the
// retrieved value (or "nil") for retrieve. This is what lets oracles.py
// express both a purely sequential script and an interleaved one (begin
// both callers before either commits) as the same flat list of tokens.

import Foundation

let registry = LoginRegistry()
var pending: [String: PendingStore] = [:]

for token in CommandLine.arguments.dropFirst() {
    let parts = token.split(separator: ":").map(String.init)
    switch parts.first {
    case "begin":
        guard parts.count == 4, let rawKind = Int(parts[2]), let kind = LoginKind(rawValue: rawKind) else {
            print("bad begin token: \(token)")
            exit(2)
        }
        pending[parts[1]] = registry.beginStore(kind: kind, value: parts[3])
        print("-")
    case "commit":
        guard parts.count == 2, let transaction = pending[parts[1]] else {
            print("bad commit token: \(token)")
            exit(2)
        }
        registry.commitStore(transaction)
        print("-")
    case "retrieve":
        guard parts.count == 2, let rawKind = Int(parts[1]), let kind = LoginKind(rawValue: rawKind) else {
            print("bad retrieve token: \(token)")
            exit(2)
        }
        print(registry.retrieve(kind: kind) ?? "nil")
    default:
        print("unknown token: \(token)")
        exit(2)
    }
}
