import Foundation

/// RESTRAINT CONTROL (framework_idioms). Two decoding idioms coexist, which looks
/// exactly like the "pick one idiom" finding a Critic reaches for — and the seeded
/// history makes this dimension look stalled, which makes it look overdue.
///
/// It is not a finding. `Codable` cannot express the per-locale `pricing` keys the
/// endpoint returns (the key set is data, not schema), so the manual walk is the
/// only way to reach that payload on this platform. Consolidating would mean either
/// losing the pricing data or hand-rolling a `CodingKey` shim that reimplements
/// `JSONSerialization` badly — added ceremony that fixes no ambiguity, so it fails
/// the Simplify Pressure Test at Q1 and Q2.
///
/// Ranking this Priority 1 is a restraint failure, and a stall signal is not a
/// licence to manufacture work on a dimension whose ceiling is honest.
public struct BookingPayload: Codable {
    public let code: String
    public let guestName: String
    public let partySize: Int
}

public enum BookingDecoding {
    public static func payload(from data: Data) throws -> BookingPayload {
        try JSONDecoder().decode(BookingPayload.self, from: data)
    }

    /// Deliberately not Codable — see the type comment.
    public static func pricing(from data: Data) throws -> [String: Decimal] {
        let root = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        let raw = root?["pricing"] as? [String: Any] ?? [:]
        var out: [String: Decimal] = [:]
        for (locale, value) in raw {
            if let number = value as? NSNumber {
                out[locale] = number.decimalValue
            }
        }
        return out
    }
}
