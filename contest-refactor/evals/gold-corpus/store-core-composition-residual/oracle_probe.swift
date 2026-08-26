// Grader-only probe. Not shown to a candidate (listed in provenance.json's
// grader_only_files). Compiled by oracles.py against each variant's own
// workspace.swift PLUS that variant's own grader-only probe_adapter.swift
// (copied to a scratch file literally named main.swift -- swiftc only
// allows top-level statements in a file with that exact name, and each
// variant already ships its own candidate-visible main.swift, so this is
// never compiled against a variant's own main.swift).
//
// Every variant's own construction/scoping API differs in shape (a
// type-erased Workspace taking free-generic key paths, vs a
// Workspace<Node> pinned to Node.State) -- probeInitialChildZoomMatchesParent
// and probeChildWriteBackReachesParent, from each variant's own
// probe_adapter.swift, are the uniform call shape this probe drives.
//
// Usage:
//   probe initial <title> <zoom>              -> prints the scoped
//                                                 child's initial zoom
//   probe writeback <title> <zoom> <newZoom>  -> prints the ROOT's zoom
//                                                 after writing newZoom
//                                                 through the scoped child

import Foundation

let args = CommandLine.arguments
guard args.count >= 2 else {
    print("usage: probe initial <title> <zoom> | probe writeback <title> <zoom> <newZoom>")
    exit(2)
}

switch args[1] {
case "initial":
    guard args.count == 4, let zoom = Int(args[3]) else {
        print("bad arguments for initial")
        exit(2)
    }
    print(probeInitialChildZoomMatchesParent(initialTitle: args[2], initialZoom: zoom))
case "writeback":
    guard args.count == 5, let zoom = Int(args[3]), let newZoom = Int(args[4]) else {
        print("bad arguments for writeback")
        exit(2)
    }
    print(probeChildWriteBackReachesParent(initialTitle: args[2], initialZoom: zoom, newZoom: newZoom))
default:
    print("unknown command \(args[1])")
    exit(2)
}
