import Foundation

/// A caller that depends on `Pricing.computeTotal(_:)` by name. This file is OUTSIDE
/// the finding's blast radius (it is in avoid[]). It exists so that renaming
/// `computeTotal` in Pricing.swift — without touching this file — fails to compile,
/// giving `run_tests.sh` a deterministic, model-independent build break.
struct PricingClient {
    func checkoutTotal() -> Int {
        Pricing().computeTotal([1, 2, 3])
    }
}
