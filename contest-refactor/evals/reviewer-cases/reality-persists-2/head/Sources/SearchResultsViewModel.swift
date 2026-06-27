import Foundation
import Combine

@MainActor
final class SearchResultsViewModel: ObservableObject {
    @Published var filters: [String] = []   // still an independent copy
    @Published var results: [String] = []
    private var lastRefreshed: Date?

    /// Syncs filters from the filter panel. Must be called whenever filterVM changes.
    func refreshFilters(from filterVM: SearchFilterViewModel) {
        filters = filterVM.activeFilters   // still a manual copy — same divergence risk
        lastRefreshed = Date()
        performSearch()
    }

    private func performSearch() {
        results = filters.isEmpty ? allItems : allItems.filter { item in
            filters.contains(where: { item.contains($0) })
        }
    }

    private let allItems = ["Apple", "Apricot", "Banana", "Blueberry", "Cherry"]
}
