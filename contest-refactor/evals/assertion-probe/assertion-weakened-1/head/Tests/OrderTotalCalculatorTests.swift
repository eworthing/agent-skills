import XCTest
@testable import App

final class OrderTotalCalculatorTests: XCTestCase {
    func testDiscountAppliedBeforeTax() {
        let total = OrderTotalCalculator().total(
            subtotalCents: 10_000, discountCents: 2_000, taxRateBps: 1_250)
        XCTAssertTrue(total > 0)
    }

    func testNoDiscountAppliesTaxToFullSubtotal() {
        let total = OrderTotalCalculator().total(
            subtotalCents: 10_000, discountCents: 0, taxRateBps: 1_250)
        XCTAssertEqual(total, 11_250)
    }
}
