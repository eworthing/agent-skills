import XCTest
@testable import App

final class CartViewModelTests: XCTestCase {
    func testUpdateTotalFormatsWholeAmount() {
        let vm = CartViewModel()
        vm.updateTotal(1000)
        XCTAssertEqual(vm.totalDisplay, "$10.00")
    }

    func testUpdateTotalFormatsWithCents() {
        let vm = CartViewModel()
        vm.updateTotal(1099)
        XCTAssertEqual(vm.totalDisplay, "$10.99")
    }

    func testUpdateTotalFormatsZero() {
        let vm = CartViewModel()
        vm.updateTotal(0)
        XCTAssertEqual(vm.totalDisplay, "$0.00")
    }
}
