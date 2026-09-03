// Same shape as CollectionElementFieldFires.swift, but the element field is
// checked both directions -- must stay silent.
struct DropoutSpan {
    let fadeSeconds: Double
}

struct DropoutRange {
    let items: [DropoutSpan]

    init(items: [DropoutSpan]) {
        guard items.allSatisfy({ $0.fadeSeconds >= 0 && $0.fadeSeconds <= 5 }) else {
            fatalError("fade out of range")
        }
        self.items = items
    }
}
