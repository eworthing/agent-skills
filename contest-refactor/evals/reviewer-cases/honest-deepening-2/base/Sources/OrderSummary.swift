import Foundation

struct LineItem {
    let name: String
    let price: Double
}

/// Summary of an order. `itemCount` is a stored copy of `items.count`, kept in
/// sync by hand in every mutator — a second source of truth for a value already
/// fully determined by `items`. A future mutator that forgets to update it leaves
/// the count silently wrong.
final class OrderSummary {
    private(set) var items: [LineItem] = []
    private(set) var itemCount: Int = 0

    func add(_ item: LineItem) {
        items.append(item)
        itemCount += 1
    }

    func remove(at index: Int) {
        items.remove(at: index)
        itemCount -= 1
    }

    var subtotal: Double {
        items.reduce(0) { $0 + $1.price }
    }
}
