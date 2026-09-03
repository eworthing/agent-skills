// fid 202 shape (PlaybackSpec.init): an array-typed parameter validated via
// allSatisfy over an element field with only an upper bound -- treat the
// field as a name and apply the same one-sided rule. Upper-only always
// fires (negatives admitted).
struct DropoutSpan {
    let fadeSeconds: Double
}

struct DropoutRange {
    let items: [DropoutSpan]

    init(items: [DropoutSpan]) {
        guard items.allSatisfy({ $0.fadeSeconds <= 5 }) else {
            fatalError("fade too long")
        }
        self.items = items
    }
}
