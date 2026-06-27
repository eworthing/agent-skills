import Foundation

@MainActor
final class CartViewModel: ObservableObject {
    @Published var totalDisplay = "$0.00"

    private var totalCents: Int = 0

    func updateTotal(_ cents: Int) {
        totalCents = cents
        // Inlined: PriceFormatter had a trivial one-line interface with no Depth.
        totalDisplay = String(format: "$%.2f", Double(cents) / 100)
    }
}
