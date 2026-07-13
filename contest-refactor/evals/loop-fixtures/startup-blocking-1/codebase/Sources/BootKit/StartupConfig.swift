import Foundation

/// Configuration assembled from the on-disk config directory.
public struct StartupConfig: Equatable {
    public struct Features: Codable, Equatable {
        public let enabled: [String]
    }

    public struct Theme: Codable, Equatable {
        public let accent: String
    }

    public struct LocaleSettings: Codable, Equatable {
        public let identifier: String
    }

    public struct Telemetry: Codable, Equatable {
        public let endpoint: String
    }

    public struct Shortcuts: Codable, Equatable {
        public let bindings: [String: String]
    }

    public let features: Features
    public let theme: Theme
    public let locale: LocaleSettings
    public let telemetry: Telemetry
    public let shortcuts: Shortcuts

    /// Loads every config document from `directory`. Called from the executable's
    /// entry point before the first prompt is printed.
    public static func loadAll(from directory: URL) throws -> StartupConfig {
        let decoder = JSONDecoder()
        let features = try decoder.decode(
            Features.self,
            from: Data(contentsOf: directory.appendingPathComponent("features.json"))
        )
        let theme = try decoder.decode(
            Theme.self,
            from: Data(contentsOf: directory.appendingPathComponent("theme.json"))
        )
        let locale = try decoder.decode(
            LocaleSettings.self,
            from: Data(contentsOf: directory.appendingPathComponent("locale.json"))
        )
        let telemetry = try decoder.decode(
            Telemetry.self,
            from: Data(contentsOf: directory.appendingPathComponent("telemetry.json"))
        )
        let shortcuts = try decoder.decode(
            Shortcuts.self,
            from: Data(contentsOf: directory.appendingPathComponent("shortcuts.json"))
        )
        return StartupConfig(
            features: features,
            theme: theme,
            locale: locale,
            telemetry: telemetry,
            shortcuts: shortcuts
        )
    }

    /// One-line description shown as the first prompt output.
    public var summary: String {
        "features=\(features.enabled.count) theme=\(theme.accent) locale=\(locale.identifier)"
    }
}

/// Cold diagnostics path: reads one report on demand when an operator asks for it.
public enum Diagnostics {
    public struct Report: Codable, Equatable {
        public let notes: [String]
    }

    /// Invoked from the `diagnose` subcommand only — never at startup.
    public static func loadReport(at url: URL) throws -> Report {
        try JSONDecoder().decode(Report.self, from: Data(contentsOf: url))
    }
}
