import Foundation

/// Fetches confirmation records for a set of reservations from the third-party
/// confirmations endpoint.
public struct ReservationLoader {
    private let fetch: (String) async throws -> Confirmation

    public init(fetch: @escaping (String) async throws -> Confirmation) {
        self.fetch = fetch
    }

    public func confirmations(for reservations: [Reservation]) async throws -> [Confirmation] {
        var out: [Confirmation] = []
        for reservation in reservations {
            out.append(try await fetch(reservation.code))
        }
        return out
    }
}

public struct Confirmation {
    public let code: String
    public let confirmedAt: Date

    public init(code: String, confirmedAt: Date) {
        self.code = code
        self.confirmedAt = confirmedAt
    }
}
