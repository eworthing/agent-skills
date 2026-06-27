import XCTest
@testable import App

final class PriceFormatterTests: XCTestCase {
    func testFormatsWholeAmount() {
        XCTAssertEqual(PriceFormatter().string(from: 1000), "$10.00")
    }

    func testFormatsWithCents() {
        XCTAssertEqual(PriceFormatter().string(from: 1099), "$10.99")
    }

    func testFormatsZero() {
        XCTAssertEqual(PriceFormatter().string(from: 0), "$0.00")
    }
}
