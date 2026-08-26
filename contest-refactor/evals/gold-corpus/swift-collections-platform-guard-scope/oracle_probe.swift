// Grader-only probe. Not shown to a candidate (listed in provenance.json's
// grader_only_files). Compiled by oracles.py against each variant's own
// platform_support.swift in turn (never against main.swift -- two files
// with top-level statements can't coexist in one swiftc invocation), so
// this is the one place both `isPotentiallyAffected` and `guardAdmits`
// get called uniformly across variants, whatever each one's internals
// look like.
//
// Usage:
//   probe affected <platform> <major> <minor>   -> prints "true"/"false"
//   probe admits <platform>                     -> prints "true"/"false"

import Foundation

let args = CommandLine.arguments
guard args.count >= 2 else {
    print("usage: probe affected <platform> <major> <minor> | probe admits <platform>")
    exit(2)
}

switch args[1] {
case "affected":
    guard args.count == 5,
        let platform = Platform(rawValue: args[2]),
        let major = Int(args[3]),
        let minor = Int(args[4])
    else {
        print("bad arguments for affected")
        exit(2)
    }
    print(isPotentiallyAffected(platform: platform, version: Version(major: major, minor: minor)))
case "admits":
    guard args.count == 3, let platform = Platform(rawValue: args[2]) else {
        print("bad arguments for admits")
        exit(2)
    }
    print(guardAdmits(platform))
default:
    print("unknown command \(args[1])")
    exit(2)
}
