import Foundation

/// Formats a price in US cents as a localised dollar string.
struct PriceFormatter {
    func string(from cents: Int) -> String {
        String(format: "$%.2f", Double(cents) / 100)
    }
}
