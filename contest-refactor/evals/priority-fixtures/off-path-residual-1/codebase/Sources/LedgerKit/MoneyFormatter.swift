import Foundation

/// Display helpers for the ledger's summary header. Presentation only — nothing
/// here is persisted, posted, or used in a balance calculation.
public enum MoneyFormatter {
    /// Compact form for the header chip: anything at a million or above collapses
    /// to a short form so the chip does not reflow.
    public static func compact(_ amountMinor: Int) -> String {
        let units = amountMinor / 100
        if units >= 1_000_000 {
            return "\(units / 1_000_000)M"
        }
        if units >= 1_000 {
            return "\(units / 1_000)k"
        }
        return "\(units)"
    }

    public static func sign(_ amountMinor: Int) -> String {
        amountMinor < 0 ? "−" : "+"
    }

    public static func accountInitial(_ account: String) -> String {
        account.first.map(String.init)?.uppercased() ?? "?"
    }
}
