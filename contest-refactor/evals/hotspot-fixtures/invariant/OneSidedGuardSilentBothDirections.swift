struct BoundedSpec {
    let rate: Double

    init(rate: Double) {
        guard rate > 0, rate < 1 else {
            self.rate = 0
            return
        }
        self.rate = rate
    }
}
