import Foundation

@MainActor
final class CartViewModel: ObservableObject {
    @Published var totalDisplay = "$0.00"

    private let formatter = PriceFormatter()
    private var totalCents: Int = 0

    func updateTotal(_ cents: Int) {
        totalCents = cents
        totalDisplay = formatter.string(from: cents)
    }
}
