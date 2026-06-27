import Foundation
import Combine

struct CartItem: Identifiable {
    let id: UUID
    let name: String
    let price: Double
}

@MainActor
final class CartViewModel: ObservableObject {
    @Published var items: [CartItem] = []

    func add(_ item: CartItem) {
        items.append(item)
    }

    func remove(id: UUID) {
        items.removeAll { $0.id == id }
    }
}
