import Foundation

/// Order total = (subtotal - discount), then tax on the discounted amount.
struct OrderTotalCalculator {
    private let discounts = DiscountApplier()

    func total(subtotalCents: Int, discountCents: Int, taxRateBps: Int) -> Int {
        let discounted = discounts.apply(subtotalCents: subtotalCents, discountCents: discountCents)
        return discounted + (discounted * taxRateBps) / 10_000
    }
}
