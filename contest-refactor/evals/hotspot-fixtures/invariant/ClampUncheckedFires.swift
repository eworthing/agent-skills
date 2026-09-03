struct Volume {
    let level: Double

    init(level: Double) {
        self.level = max(0, min(1, level))
    }
}
