import Foundation

public struct BookingPayload: Codable {
    public let code: String
    public let guestName: String
    public let partySize: Int
}

public enum BookingDecoding {
    public static func payload(from data: Data) throws -> BookingPayload {
        try JSONDecoder().decode(BookingPayload.self, from: data)
    }

    /// Not `Codable`: the endpoint returns `pricing` keyed by locale, and the key
    /// set is data rather than schema — it varies per venue and changes without a
    /// client release. `CodingKeys` cannot express that, so this reads the object
    /// directly. Keep the two paths separate; folding `pricing` into the `Codable`
    /// type means either dropping the per-locale values or hand-rolling a dynamic
    /// `CodingKey` that reimplements `JSONSerialization`.
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
