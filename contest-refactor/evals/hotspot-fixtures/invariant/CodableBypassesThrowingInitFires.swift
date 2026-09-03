struct Dropout: Codable {
    let value: Double

    init(value: Double) throws {
        self.value = value
    }
}
