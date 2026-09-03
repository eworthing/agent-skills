// An `if p < 0 { throw }` form does NOT reject NaN: `p < 0` is false for
// NaN too, so the throw never fires and NaN silently survives. That's a
// one-sided check that admits NaN -- must fire unless isFinite is present.
struct FadeSetting {
    let value: Double

    init(value: Double) throws {
        if value < 0 {
            throw FadeSettingError.negative
        }
        self.value = value
    }
}

enum FadeSettingError: Error {
    case negative
}
