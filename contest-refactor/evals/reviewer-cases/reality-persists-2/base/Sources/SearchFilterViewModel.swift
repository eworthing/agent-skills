import Foundation
import Combine

@MainActor
final class SearchFilterViewModel: ObservableObject {
    @Published var activeFilters: [String] = []

    func addFilter(_ filter: String) {
        if !activeFilters.contains(filter) {
            activeFilters.append(filter)
        }
    }

    func removeFilter(_ filter: String) {
        activeFilters.removeAll { $0 == filter }
    }
}
