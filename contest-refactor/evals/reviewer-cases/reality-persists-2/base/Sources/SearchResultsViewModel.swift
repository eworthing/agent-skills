import Foundation
import Combine

@MainActor
final class SearchResultsViewModel: ObservableObject {
    @Published var filters: [String] = []
    @Published var results: [String] = []

    func applyFilters(from filterVM: SearchFilterViewModel) {
        filters = filterVM.activeFilters  // copy — diverges if filterVM changes later
        performSearch()
    }

    private func performSearch() {
        results = filters.isEmpty ? allItems : allItems.filter { item in
            filters.contains(where: { item.contains($0) })
        }
    }

    private let allItems = ["Apple", "Apricot", "Banana", "Blueberry", "Cherry"]
}
