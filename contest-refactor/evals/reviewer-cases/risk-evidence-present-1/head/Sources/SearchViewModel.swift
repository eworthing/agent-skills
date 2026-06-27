import Foundation
import Combine

/// Drives the search UI.  @Published mutations stay on the main actor via
/// MainActor.run; regex matching runs nonisolated to avoid blocking the render loop.
final class SearchViewModel: ObservableObject {
    @Published var query: String = ""
    @Published var results: [String] = []
    @Published var isSearching: Bool = false

    private let corpus: [String]

    init(corpus: [String]) {
        self.corpus = corpus
    }

    /// Captures query on the main actor, matches nonisolated, pushes results
    /// back via MainActor.run.  Callers must await this method.
    func executeSearch() async {
        let currentQuery = await MainActor.run { query }
        guard !currentQuery.isEmpty else {
            await MainActor.run { results = [] }
            return
        }
        await MainActor.run { isSearching = true }
        let pattern = (try? NSRegularExpression(pattern: currentQuery)) ?? NSRegularExpression()
        let matched = corpus.filter { item in
            let range = NSRange(item.startIndex..., in: item)
            return pattern.firstMatch(in: item, range: range) != nil
        }
        await MainActor.run {
            results = matched
            isSearching = false
        }
    }
}
