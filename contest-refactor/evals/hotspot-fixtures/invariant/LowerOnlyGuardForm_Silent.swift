import Foundation

// Lower bound only, in guard form: `nan >= 0` is false, so NaN and negatives
// are both rejected. This is the canonical Swift validation idiom and must
// stay silent (only +inf survives, which the rule does not flag).
struct FadeSetting {
    let value: Double

    init(value: Double) throws {
        guard value >= 0 else {
            throw FadeSettingError.negative
        }
        self.value = value
    }
}

enum FadeSettingError: Error {
    case negative
}
