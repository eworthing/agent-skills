import Foundation

/// Sums line-item prices for the checkout total.
///
/// NOTE (planted fixture): a caller in the same module (PricingClient) depends on
/// this method's name, and `run_tests.sh` typechecks both files together. A Step-3
/// rename that respects the blast radius (this file only) breaks the caller's
/// compilation deterministically, forcing the Step-3 sub-step-3 revert.
struct Pricing {
    func computeTotal(_ items: [Int]) -> Int {
        items.reduce(0, +)
    }
}
