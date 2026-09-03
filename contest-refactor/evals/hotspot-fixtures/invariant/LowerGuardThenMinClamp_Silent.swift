// fid 131 shape (AppSettings.init): a guard-form lower-bound check rejects
// NaN on its own, and a later `min(` clamp on the same name closes the
// upper bound too -- the pair is a complete, safe range check. Neither
// one_sided_guard nor clamp_unchecked may fire on `value` here.
struct FadeSetting {
    let value: Double

    init(value: Double) {
        guard value >= 0 else {
            fatalError("negative")
        }
        self.value = min(value, 10)
    }
}
