import XCTest
@testable import App

// Residual: PriceFormatter was deleted in this loop. This file should be
// deleted entirely; the remaining test duplicates coverage already in
// CartViewModelTests.testUpdateTotalFormatsZero.
final class PriceFormatterTests: XCTestCase {
    func testFormatsZero() {
        let vm = CartViewModel()
        vm.updateTotal(0)
        XCTAssertEqual(vm.totalDisplay, "$0.00")
    }
}
