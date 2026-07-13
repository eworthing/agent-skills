import Foundation

/// Formats numeric values with a fixed unit suffix.
///
/// Near-miss restraint control for the D1 (recomputed-derived-value) detector: the
/// stored `unit` is read on every iteration of `format`, but a stored-property read is
/// O(1) with no derivation cost, so repeated reads are NOT a recomputed-derived-value
/// defect. An efficiency finding against this type is over-flagging.
public struct UnitFormatter: Equatable {
    public let unit: String

    public init(unit: String) {
        self.unit = unit
    }

    public func format(_ values: [Double]) -> [String] {
        values.map { "\(Self.format($0)) \(unit)" }
    }

    private static func format(_ value: Double) -> String {
        String(format: "%.2f", value)
    }
}
