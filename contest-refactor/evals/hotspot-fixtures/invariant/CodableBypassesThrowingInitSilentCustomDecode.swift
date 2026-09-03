struct Dropout: Codable {
    let value: Double

    init(value: Double) throws {
        self.value = value
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        let value = try container.decode(Double.self)
        guard value.isFinite else {
            throw DecodingError.dataCorruptedError(
                in: container, debugDescription: "non-finite value"
            )
        }
        self.value = value
    }
}
