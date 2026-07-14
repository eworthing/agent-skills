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
        return StartupConfig(
            features: try load(Features.self, "features.json", from: directory, using: decoder),
            theme: try load(Theme.self, "theme.json", from: directory, using: decoder),
            locale: try load(LocaleSettings.self, "locale.json", from: directory, using: decoder),
            telemetry: try load(Telemetry.self, "telemetry.json", from: directory, using: decoder),
            shortcuts: try load(Shortcuts.self, "shortcuts.json", from: directory, using: decoder)
        )
    }

    /// Reads and decodes one config document from `directory`.
    private static func load<Document: Codable>(
        _ type: Document.Type,
        _ name: String,
        from directory: URL,
        using decoder: JSONDecoder
    ) throws -> Document {
        try decoder.decode(type, from: Data(contentsOf: directory.appendingPathComponent(name)))
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
