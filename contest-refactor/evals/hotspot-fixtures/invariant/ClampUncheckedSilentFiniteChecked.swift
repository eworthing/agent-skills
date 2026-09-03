struct Volume {
    let level: Double

    init(level: Double) {
        self.level = level.isFinite ? max(0, min(1, level)) : 0
    }
}
