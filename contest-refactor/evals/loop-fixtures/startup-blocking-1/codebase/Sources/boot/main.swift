import BootKit
import Foundation

let arguments = CommandLine.arguments
let configPath = arguments.count > 1 && arguments[1] != "diagnose" ? arguments[1] : "config"
let configDirectory = URL(fileURLWithPath: configPath, isDirectory: true)

let config = try StartupConfig.loadAll(from: configDirectory)
print(config.summary)

if arguments.contains("diagnose") {
    let report = try Diagnostics.loadReport(
        at: configDirectory.appendingPathComponent("diagnostics.json")
    )
    print("diagnostics: \(report.notes.count) note(s)")
}
