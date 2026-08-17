import XCTest
@testable import App

final class DiscountApplierTests: XCTestCase {
    func testSubtractsDiscount() {
        XCTAssertEqual(DiscountApplier().apply(subtotalCents: 10_000, discountCents: 2_000), 8_000)
    }

    func testFloorsAtZero() {
        XCTAssertEqual(DiscountApplier().apply(subtotalCents: 1_000, discountCents: 5_000), 0)
    }
}
