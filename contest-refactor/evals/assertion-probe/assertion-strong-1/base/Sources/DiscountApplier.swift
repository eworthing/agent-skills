import Foundation

/// Applies a flat discount to a subtotal. Shallow: the Interface is one function
/// whose Implementation is one subtraction.
struct DiscountApplier {
    func apply(subtotalCents: Int, discountCents: Int) -> Int {
        max(0, subtotalCents - discountCents)
    }
}
