import Foundation
import Combine

@MainActor
final class CheckoutViewModel: ObservableObject {
    @Published var lineItems: [CartItem] = []   // independent copy

    var total: Double {
        lineItems.reduce(0) { $0 + $1.price }
    }

    func sync(from cart: CartViewModel) {
        lineItems = cart.items   // manual sync — stale if cart changes after this
    }
}
