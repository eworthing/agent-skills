import Foundation

struct LineItem {
    let name: String
    let price: Double
}

/// Summary of an order. `itemCount` derives directly from `items` — a single
/// source of truth that cannot drift.
final class OrderSummary {
    private(set) var items: [LineItem] = []

    // Derived from the single authoritative source — no stored copy to sync.
    var itemCount: Int { items.count }

    func add(_ item: LineItem) {
        items.append(item)
    }

    func remove(at index: Int) {
        items.remove(at: index)
    }

    var subtotal: Double {
        items.reduce(0) { $0 + $1.price }
    }
}
