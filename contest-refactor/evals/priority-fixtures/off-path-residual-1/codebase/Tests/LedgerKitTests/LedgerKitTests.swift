import XCTest

@testable import LedgerKit

final class SplitTests: XCTestCase {
    func testPartsSumBackToTheTotal() {
        for total in [0, 1, 99, 100, 1001, -7] {
            for ways in 1...5 {
                XCTAssertEqual(Split.evenly(total, ways: ways).reduce(0, +), total,
                               "total=\(total) ways=\(ways)")
            }
        }
    }

    func testRemainderGoesToTheFirstPart() {
        XCTAssertEqual(Split.evenly(100, ways: 3), [34, 33, 33])
    }

    func testExactDivisionHasNoRemainder() {
        XCTAssertEqual(Split.evenly(99, ways: 3), [33, 33, 33])
    }

    func testZeroWaysIsEmpty() {
        XCTAssertTrue(Split.evenly(100, ways: 0).isEmpty)
    }
}

final class SettlementTests: XCTestCase {
    func testOnePostingPerAccount() {
        let out = Settlement.postings(total: 300, across: ["a", "b", "c"])
        XCTAssertEqual(out.map(\.account), ["a", "b", "c"])
    }

    func testExactDivisionSettlesTheWholeBill()
    {
        let out = Settlement.postings(total: 300, across: ["a", "b", "c"])
        XCTAssertEqual(out.reduce(0) { $0 + $1.amountMinor }, 300)
    }

    func testNoAccountsIsEmpty() {
        XCTAssertTrue(Settlement.postings(total: 300, across: []).isEmpty)
    }

    func testMemoIsSet() {
        let out = Settlement.postings(total: 100, across: ["a"])
        XCTAssertEqual(out.first?.memo, "settlement")
    }
}

final class MoneyFormatterTests: XCTestCase {
    func testPlainUnitsBelowAThousand() {
        XCTAssertEqual(MoneyFormatter.compact(0), "0")
        XCTAssertEqual(MoneyFormatter.compact(12_34), "12")
        XCTAssertEqual(MoneyFormatter.compact(99_900), "999")
    }

    func testThousandsCollapse() {
        XCTAssertEqual(MoneyFormatter.compact(100_000), "1k")
        XCTAssertEqual(MoneyFormatter.compact(2_500_00), "2k")
    }

    func testSignIsNegativeOnlyBelowZero() {
        XCTAssertEqual(MoneyFormatter.sign(-1), "−")
        XCTAssertEqual(MoneyFormatter.sign(0), "+")
        XCTAssertEqual(MoneyFormatter.sign(5), "+")
    }

    func testAccountInitialIsUppercased() {
        XCTAssertEqual(MoneyFormatter.accountInitial("assets:cash"), "A")
    }

    func testAccountInitialFallsBackForEmpty() {
        XCTAssertEqual(MoneyFormatter.accountInitial(""), "?")
    }
}
