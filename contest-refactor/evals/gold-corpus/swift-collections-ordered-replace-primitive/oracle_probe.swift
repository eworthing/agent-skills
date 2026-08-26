// Grader-only probe. Not shown to a candidate (listed in provenance.json's
// grader_only_files). Compiled by oracles.py against each variant's own
// ordered_replace.swift in turn (never against main.swift -- two files
// with top-level statements can't coexist in one swiftc invocation), so
// this is the one place both `Roster.replace` and `Ledger.replaceLabel`
// get called uniformly across variants, whatever each one's internals
// look like.
//
// Usage:
//   probe roster-replace <old> <new> <items,comma,separated>
//   probe ledger-replace <old> <new> <newValue> <items,comma,separated> <values,comma,separated>
//
// Both print three lines: the outcome (success, or trapped:<message>), the
// resulting storage, and the lookup count -- everything oracles.py needs to
// check diagnostics, contents, and lookup work from one probe invocation.

import Foundation

func outcomeLine(_ outcome: ReplaceOutcome) -> String {
    switch outcome {
    case .success:
        return "outcome: success"
    case .trapped(let message):
        return "outcome: trapped:\(message)"
    }
}

func splitList(_ raw: String) -> [String] {
    raw.isEmpty ? [] : raw.split(separator: ",").map(String.init)
}

let args = CommandLine.arguments
guard args.count >= 2 else {
    print(
        "usage: probe roster-replace <old> <new> <items> | "
            + "probe ledger-replace <old> <new> <newValue> <items> <values>"
    )
    exit(2)
}

switch args[1] {
case "roster-replace":
    guard args.count == 5 else {
        print("bad arguments for roster-replace")
        exit(2)
    }
    var roster = Roster(items: splitList(args[4]))
    let outcome = roster.replace(args[2], with: args[3])
    print(outcomeLine(outcome))
    print("items: \(roster.items.joined(separator: ","))")
    print("lookups: \(roster.lookupCount)")
case "ledger-replace":
    guard args.count == 7, let newValue = Int(args[4]) else {
        print("bad arguments for ledger-replace")
        exit(2)
    }
    let values = splitList(args[6]).compactMap { Int($0) }
    var ledger = Ledger(roster: Roster(items: splitList(args[5])), values: values)
    let outcome = ledger.replaceLabel(args[2], with: args[3], value: newValue)
    print(outcomeLine(outcome))
    print("items: \(ledger.roster.items.joined(separator: ","))")
    print("values: \(ledger.values.map(String.init).joined(separator: ","))")
    print("lookups: \(ledger.lookupCount)")
default:
    print("unknown command \(args[1])")
    exit(2)
}
