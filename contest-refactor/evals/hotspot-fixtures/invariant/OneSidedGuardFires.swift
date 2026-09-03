import Foundation

// Upper bound only: a negative rate passes straight through. The invariant
// queue must fire `one_sided_guard` on `rate`.
struct PlaybackSpec {
    let rate: Double

    init(rate: Double) {
        guard rate <= 4 else {
            self.rate = 4
            return
        }
        self.rate = rate
    }
}
