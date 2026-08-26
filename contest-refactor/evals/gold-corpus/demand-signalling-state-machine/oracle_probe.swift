// Grader-only probe. Not shown to a candidate (listed in provenance.json's
// grader_only_files). Compiled by oracles.py against each variant's own
// signal_relay.swift in turn (never against main.swift -- two files with
// top-level statements can't coexist in one swiftc invocation), so this is
// the one place `Relay.step` gets driven uniformly across variants whose
// internals differ.
//
// Usage:
//   probe <sourceCount> <event> [<event> ...]
//
// Each event is one of:
//   demand:<requestID>
//   produce:<sourceID>:<value>
//   finish:<sourceID>
//   cancel
//
// One line of output per event, in order: the actions that event's step()
// call returned, joined by a single space ("start:0 resume:1:2"), or the
// literal "EMPTY" if step() returned no actions for that event.

import Foundation

func describe(_ action: RelayAction) -> String {
    switch action {
    case .resumeWithValue(let request, let value):
        return "resume:\(request):\(value)"
    case .resumeWithFinish(let request):
        return "finish:\(request)"
    case .startSourceWork(let source):
        return "start:\(source.rawValue)"
    }
}

let args = CommandLine.arguments
guard args.count >= 2, let sourceCount = Int(args[1]) else {
    print("usage: probe <sourceCount> <event> [<event> ...]")
    exit(2)
}

let relay = Relay(sourceCount: sourceCount)

for token in args.dropFirst(2) {
    let parts = token.split(separator: ":").map(String.init)
    let event: RelayEvent
    switch parts.first {
    case "demand":
        guard parts.count == 2, let request = Int(parts[1]) else {
            print("bad demand token: \(token)")
            exit(2)
        }
        event = .demandArrived(request: request)
    case "produce":
        guard parts.count == 3, let rawSource = Int(parts[1]), let source = SourceID(rawValue: rawSource),
            let value = Int(parts[2])
        else {
            print("bad produce token: \(token)")
            exit(2)
        }
        event = .valueProduced(source: source, value: value)
    case "finish":
        guard parts.count == 2, let rawSource = Int(parts[1]), let source = SourceID(rawValue: rawSource) else {
            print("bad finish token: \(token)")
            exit(2)
        }
        event = .sourceFinished(source: source)
    case "cancel":
        event = .cancelled
    default:
        print("unknown token: \(token)")
        exit(2)
    }
    let actions = relay.step(event)
    print(actions.isEmpty ? "EMPTY" : actions.map(describe).joined(separator: " "))
}
