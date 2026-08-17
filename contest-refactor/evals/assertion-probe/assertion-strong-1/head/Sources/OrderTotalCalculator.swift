import Foundation

/// Order total, with the discount step inlined (DiscountApplier deleted).
struct OrderTotalCalculator {
    func total(subtotalCents: Int, discountCents: Int, taxRateBps: Int) -> Int {
        let discounted = max(0, subtotalCents - discountCents)
        return discounted + (discounted * taxRateBps) / 10_000
    }
}
