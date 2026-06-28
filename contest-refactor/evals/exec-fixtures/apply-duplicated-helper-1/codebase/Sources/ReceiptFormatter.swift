import Foundation

/// Unrelated bystander: formats a receipt header string. Must stay untouched
/// by a Step-3 fix targeting OrderCalculator's duplicated pricing arithmetic.
struct ReceiptFormatter {
    func header(for storeName: String) -> String {
        return "=== \(storeName) ==="
    }
}
