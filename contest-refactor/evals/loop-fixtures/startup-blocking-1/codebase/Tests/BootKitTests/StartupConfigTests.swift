import XCTest

@testable import BootKit

final class StartupConfigTests: XCTestCase {
    private var configDirectory: URL!

    override func setUpWithError() throws {
        configDirectory = URL(fileURLWithPath: NSTemporaryDirectory(), isDirectory: true)
            .appendingPathComponent("boot-config-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: configDirectory, withIntermediateDirectories: true)
        let documents: [String: String] = [
            "features.json": #"{"enabled": ["search", "sync"]}"#,
            "theme.json": #"{"accent": "teal"}"#,
            "locale.json": #"{"identifier": "en_US"}"#,
            "telemetry.json": #"{"endpoint": "https://telemetry.example"}"#,
            "shortcuts.json": #"{"bindings": {"save": "cmd-s"}}"#,
            "diagnostics.json": #"{"notes": ["disk ok", "network ok"]}"#,
        ]
        for (name, contents) in documents {
            try contents.write(
                to: configDirectory.appendingPathComponent(name),
                atomically: true,
                encoding: .utf8
            )
        }
    }

    override func tearDownWithError() throws {
        try FileManager.default.removeItem(at: configDirectory)
    }

    func testLoadAllDecodesEveryDocument() throws {
        let config = try StartupConfig.loadAll(from: configDirectory)
        XCTAssertEqual(config.features.enabled, ["search", "sync"])
        XCTAssertEqual(config.theme.accent, "teal")
        XCTAssertEqual(config.locale.identifier, "en_US")
        XCTAssertEqual(config.telemetry.endpoint, "https://telemetry.example")
        XCTAssertEqual(config.shortcuts.bindings, ["save": "cmd-s"])
    }

    func testSummaryDescribesLoadedConfig() throws {
        let config = try StartupConfig.loadAll(from: configDirectory)
        XCTAssertEqual(config.summary, "features=2 theme=teal locale=en_US")
    }

    func testMissingDocumentThrows() {
        try? FileManager.default.removeItem(
            at: configDirectory.appendingPathComponent("theme.json")
        )
        XCTAssertThrowsError(try StartupConfig.loadAll(from: configDirectory))
    }

    func testMalformedDocumentThrows() throws {
        try #"{"accent": 7}"#.write(
            to: configDirectory.appendingPathComponent("theme.json"),
            atomically: true,
            encoding: .utf8
        )
        XCTAssertThrowsError(try StartupConfig.loadAll(from: configDirectory))
    }

    func testDiagnosticsReportLoadsOnDemand() throws {
        let report = try Diagnostics.loadReport(
            at: configDirectory.appendingPathComponent("diagnostics.json")
        )
        XCTAssertEqual(report.notes, ["disk ok", "network ok"])
    }
}
