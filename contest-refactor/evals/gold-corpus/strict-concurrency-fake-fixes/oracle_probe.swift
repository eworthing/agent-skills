// Grader-only probe. Not shown to a candidate (listed in provenance.json's
// grader_only_files). Compiled by oracles.py against each variant's own
// hit_counter.swift PLUS that variant's own grader-only probe_adapter.swift
// (copied to a scratch file literally named main.swift -- swiftc only
// allows top-level statements in a file with that exact name, and each
// variant already ships its own candidate-visible main.swift, so this is
// never compiled against a variant's own main.swift).
//
// Every variant's own probe_adapter.swift exposes the same three async
// entry points -- probeFinalCountAfterTwoLogicalCallers,
// probeOrdinaryTwoCallsGiveTwo, probeInvariantViolated -- reconciling
// each variant's real, differently-protected API into one call shape.
// All three are `async` uniformly, even for variants that never suspend,
// because the blanket-global-isolation variant's real API genuinely
// requires await and this probe drives all five variants through one
// shared CLI. Top-level `await` in a file literally named main.swift
// needs no explicit Task or async main -- Swift's top-level code is an
// implicit async context whenever it contains await.
//
// Usage:
//   probe interleaving  -> prints the final count after a scripted,
//                          fully deterministic two-caller interleaving
//   probe ordinary       -> prints the final count after two ordinary,
//                          non-adversarial sequential calls
//   probe invariant       -> prints "true" if driving the second path
//                          after setup violates this variant's own
//                          claimed invariant, "false" otherwise

import Foundation

let args = CommandLine.arguments
guard args.count == 2 else {
    print("usage: probe interleaving|ordinary|invariant")
    exit(2)
}

switch args[1] {
case "interleaving":
    print(await probeFinalCountAfterTwoLogicalCallers())
case "ordinary":
    print(await probeOrdinaryTwoCallsGiveTwo())
case "invariant":
    print(await probeInvariantViolated())
default:
    print("unknown command \(args[1])")
    exit(2)
}
