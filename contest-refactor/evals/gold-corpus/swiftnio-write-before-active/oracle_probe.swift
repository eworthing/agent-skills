// Grader-only probe. Not shown to a candidate (listed in provenance.json's
// grader_only_files). Compiled by oracles.py against each variant's own
// pipe_support.swift in turn (copied to a scratch main.swift, never the
// variant's own main.swift -- see #298's oracles.py for why).
//
// Usage: probe <ops>, a comma-separated sequence of:
//   w<N>  write(N)
//   f     flush()
//   a     activate()
// Prints the boolean result of each write call, then the final emitted
// sequence, e.g.:
//   writes:true,true
//   emitted:1,2

import Foundation

let args = CommandLine.arguments
guard args.count == 2 else {
    print("usage: probe <ops>  (e.g. w1,a,f)")
    exit(2)
}

let pipe = Pipe()
var writeResults: [Bool] = []

for op in args[1].split(separator: ",") {
    if op.hasPrefix("w"), let value = Int(op.dropFirst()) {
        writeResults.append(pipe.write(value))
    } else if op == "f" {
        pipe.flush()
    } else if op == "a" {
        pipe.activate()
    } else {
        print("bad op: \(op)")
        exit(2)
    }
}

print("writes:\(writeResults.map { $0 ? "true" : "false" }.joined(separator: ","))")
print("emitted:\(pipe.emitted.map(String.init).joined(separator: ","))")
