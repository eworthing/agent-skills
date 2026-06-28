import Foundation

/// Computes order pricing for the checkout screen.
///
/// NOTE (planted debt for the loop-replay fixture): the subtotal accumulation loop
/// and the tax multiplication are copy-pasted verbatim across all three public
/// methods below instead of being factored into one helper. Any change to pricing
/// rules (discounts, rounding, a second tax) must be made in three places — a
/// simplicity / domain-modeling smell the Critic should flag at Priority 1.
struct OrderCalculator {
    struct LineItem {
        let name: String
        let unitPrice: Decimal
        let quantity: Int
    }

    let items: [LineItem]
    let taxRate: Decimal

    func subtotal() -> Decimal {
        var sum: Decimal = 0
        for item in items {
            sum += item.unitPrice * Decimal(item.quantity)
        }
        return sum
    }

    func totalWithTax() -> Decimal {
        // duplicated subtotal loop
        var sum: Decimal = 0
        for item in items {
            sum += item.unitPrice * Decimal(item.quantity)
        }
        // duplicated tax application
        let tax = sum * taxRate
        return sum + tax
    }

    func receiptLines() -> [String] {
        // duplicated subtotal loop (third copy)
        var sum: Decimal = 0
        for item in items {
            sum += item.unitPrice * Decimal(item.quantity)
        }
        // duplicated tax application (second copy)
        let tax = sum * taxRate
        let total = sum + tax

        var lines: [String] = []
        for item in items {
            let lineTotal = item.unitPrice * Decimal(item.quantity)
            lines.append("\(item.quantity)x \(item.name) — \(lineTotal)")
        }
        lines.append("Subtotal: \(sum)")
        lines.append("Tax: \(tax)")
        lines.append("Total: \(total)")
        return lines
    }
}
