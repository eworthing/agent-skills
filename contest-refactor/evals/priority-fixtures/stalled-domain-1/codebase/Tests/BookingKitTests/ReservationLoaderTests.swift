import XCTest

@testable import BookingKit

final class ReservationLoaderTests: XCTestCase {
    private func reservations(_ codes: [String]) -> [Reservation] {
        codes.map { Reservation(code: $0, guestName: "Guest", partySize: 2) }
    }

    func testReturnsOneConfirmationPerReservationInOrder() async throws {
        let loader = ReservationLoader { code in
            Confirmation(code: code, confirmedAt: Date(timeIntervalSince1970: 0))
        }
        let out = try await loader.confirmations(for: reservations(["A-1", "B-2", "C-3"]))
        XCTAssertEqual(out.map(\.code), ["A-1", "B-2", "C-3"])
    }

    func testEmptyInputPerformsNoFetch() async throws {
        var calls = 0
        let loader = ReservationLoader { code in
            calls += 1
            return Confirmation(code: code, confirmedAt: Date())
        }
        let out = try await loader.confirmations(for: [])
        XCTAssertTrue(out.isEmpty)
        XCTAssertEqual(calls, 0)
    }

    func testFetchesExactlyOncePerReservation() async throws {
        var calls: [String] = []
        let loader = ReservationLoader { code in
            calls.append(code)
            return Confirmation(code: code, confirmedAt: Date())
        }
        _ = try await loader.confirmations(for: reservations(["A-1", "B-2"]))
        XCTAssertEqual(calls, ["A-1", "B-2"])
    }

    func testPropagatesFetchFailure() async {
        struct Boom: Error {}
        let loader = ReservationLoader { _ in throw Boom() }
        do {
            _ = try await loader.confirmations(for: reservations(["A-1"]))
            XCTFail("expected the fetch failure to propagate")
        } catch {
            XCTAssertTrue(error is Boom)
        }
    }
}
