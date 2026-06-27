import Foundation
import Combine

@MainActor
final class CheckoutViewModel: ObservableObject {
    private let cart: CartViewModel

    init(cart: CartViewModel) {
        self.cart = cart
    }

    // Derived directly from the single authoritative source — no copy
    var lineItems: [CartItem] { cart.items }

    var total: Double {
        lineItems.reduce(0) { $0 + $1.price }
    }
}
