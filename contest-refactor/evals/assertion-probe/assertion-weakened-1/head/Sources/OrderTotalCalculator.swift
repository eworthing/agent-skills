import Foundation

/// Order total, with the discount step inlined (DiscountApplier deleted).
struct OrderTotalCalculator {
    func total(subtotalCents: Int, discountCents: Int, taxRateBps: Int) -> Int {
        let taxed = subtotalCents + (subtotalCents * taxRateBps) / 10_000
        return max(0, taxed - discountCents)
    }
}
