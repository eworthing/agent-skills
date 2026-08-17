import XCTest
@testable import App

final class OrderTotalCalculatorTests: XCTestCase {
    // Pins the ordering invariant: discount is applied BEFORE tax.
    // (10_000 - 2_000) * 1.125 = 9_000. Tax-first would give 9_250.
    func testDiscountAppliedBeforeTax() {
        let total = OrderTotalCalculator().total(
            subtotalCents: 10_000, discountCents: 2_000, taxRateBps: 1_250)
        XCTAssertEqual(total, 9_000)
    }

    func testNoDiscountAppliesTaxToFullSubtotal() {
        let total = OrderTotalCalculator().total(
            subtotalCents: 10_000, discountCents: 0, taxRateBps: 1_250)
        XCTAssertEqual(total, 11_250)
    }
}
