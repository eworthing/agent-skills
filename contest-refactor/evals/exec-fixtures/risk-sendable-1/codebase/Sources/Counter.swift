import Foundation

/// A UI-facing counter. It is `@MainActor`-isolated because the value is read
/// directly by the view layer; dropping the attribute crosses an isolation /
/// Sendable boundary and needs preservation evidence (Meta-Rule 4).
@MainActor
final class Counter {
    private(set) var value = 0

    func increment() {
        value += 1
    }
}
