import XCTest

@testable import BookingKit

final class ReservationTests: XCTestCase {
    func testWellFormedAcceptsTheIssuedShape() {
        XCTAssertTrue(ReservationCheck.isWellFormed("ABCD-123456"))
    }

    func testWellFormedRejectsMissingDash() {
        XCTAssertFalse(ReservationCheck.isWellFormed("ABCD123456"))
    }

    func testWellFormedRejectsWrongBlockLengths() {
        XCTAssertFalse(ReservationCheck.isWellFormed("ABC-123456"))
        XCTAssertFalse(ReservationCheck.isWellFormed("ABCD-12345"))
    }

    func testShortCodeIsTheLetterBlock() {
        let r = Reservation(code: "ABCD-123456", guestName: "Ada Lovelace", partySize: 2)
        XCTAssertEqual(r.shortCode, "ABCD")
    }

    func testShortCodeFallsBackForShortInput() {
        let r = Reservation(code: "AB", guestName: "Ada Lovelace", partySize: 2)
        XCTAssertEqual(r.shortCode, "AB")
    }

    func testLooksUsableRejectsWhitespaceOnly() {
        let r = Reservation(code: "   ", guestName: "Ada Lovelace", partySize: 2)
        XCTAssertFalse(r.looksUsable)
    }

    func testLooksUsableAcceptsAnIssuedCode() {
        let r = Reservation(code: "ABCD-123456", guestName: "Ada Lovelace", partySize: 2)
        XCTAssertTrue(r.looksUsable)
    }
}
