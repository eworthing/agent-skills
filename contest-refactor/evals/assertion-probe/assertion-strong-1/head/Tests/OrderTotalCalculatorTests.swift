import XCTest
@testable import App

final class OrderTotalCalculatorTests: XCTestCase {
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

    // Absorbed from the deleted DiscountApplierTests: the floor-at-zero rule now
    // lives at the deepened Interface, asserted through the public entry point.
    func testDiscountLargerThanSubtotalFloorsAtZero() {
        let total = OrderTotalCalculator().total(
            subtotalCents: 1_000, discountCents: 5_000, taxRateBps: 1_250)
        XCTAssertEqual(total, 0)
    }
}
