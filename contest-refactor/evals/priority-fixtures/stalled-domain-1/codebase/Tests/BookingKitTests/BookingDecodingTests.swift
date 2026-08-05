import XCTest

@testable import BookingKit

final class BookingDecodingTests: XCTestCase {
    func testDecodesThePayload() throws {
        let data = Data(
            #"{"code":"ABCD-123456","guestName":"Ada Lovelace","partySize":4}"#.utf8
        )
        let payload = try BookingDecoding.payload(from: data)
        XCTAssertEqual(payload.code, "ABCD-123456")
        XCTAssertEqual(payload.partySize, 4)
    }

    func testDecodeRejectsAMissingField() {
        let data = Data(#"{"code":"ABCD-123456","guestName":"Ada Lovelace"}"#.utf8)
        XCTAssertThrowsError(try BookingDecoding.payload(from: data))
    }

    func testReadsEveryLocaleKeyInPricing() throws {
        let data = Data(#"{"pricing":{"en-GB":42.5,"fr-FR":48,"ja-JP":7800}}"#.utf8)
        let pricing = try BookingDecoding.pricing(from: data)
        XCTAssertEqual(Set(pricing.keys), ["en-GB", "fr-FR", "ja-JP"])
        XCTAssertEqual(pricing["en-GB"], Decimal(string: "42.5"))
    }

    func testPricingIsEmptyWhenTheKeyIsAbsent() throws {
        let data = Data(#"{"code":"ABCD-123456"}"#.utf8)
        XCTAssertTrue(try BookingDecoding.pricing(from: data).isEmpty)
    }

    func testPricingSkipsNonNumericValues() throws {
        let data = Data(#"{"pricing":{"en-GB":42.5,"de-DE":"on request"}}"#.utf8)
        let pricing = try BookingDecoding.pricing(from: data)
        XCTAssertEqual(Set(pricing.keys), ["en-GB"])
    }
}

final class BookingFormatTests: XCTestCase {
    func testPartyLabelIsSingularForOne() {
        XCTAssertEqual(BookingFormat.partyLabel(1), "1 guest")
    }

    func testPartyLabelIsPluralOtherwise() {
        XCTAssertEqual(BookingFormat.partyLabel(4), "4 guests")
    }

    func testInitialsTakesTheFirstTwoWords() {
        XCTAssertEqual(BookingFormat.initials("Ada Lovelace"), "AL")
        XCTAssertEqual(BookingFormat.initials("Grace Brewster Hopper"), "GB")
    }

    func testInitialsHandlesASingleName() {
        XCTAssertEqual(BookingFormat.initials("Ada"), "A")
    }

    func testBadgeShowsTheCountForOrdinaryValues() {
        XCTAssertEqual(BookingFormat.badge(0), "0")
        XCTAssertEqual(BookingFormat.badge(12), "12")
    }
}
