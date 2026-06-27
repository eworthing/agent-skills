import Foundation
import Combine

/// Drives the search UI.  All methods inherit @MainActor isolation because the
/// @Published properties are directly bound to SwiftUI views.
///
/// executeSearch() performs a synchronous NSRegularExpression match over the
/// full corpus on the main actor — the targeted finding.
@MainActor
final class SearchViewModel: ObservableObject {
    @Published var query: String = ""
    @Published var results: [String] = []
    @Published var isSearching: Bool = false

    private let corpus: [String]

    init(corpus: [String]) {
        self.corpus = corpus
    }

    /// Blocks the main actor: NSRegularExpression.matches runs synchronously
    /// over every corpus entry before the results are published.
    func executeSearch() {
        guard !query.isEmpty else {
            results = []
            return
        }
        isSearching = true
        let pattern = (try? NSRegularExpression(pattern: query)) ?? NSRegularExpression()
        results = corpus.filter { item in
            let range = NSRange(item.startIndex..., in: item)
            return pattern.firstMatch(in: item, range: range) != nil
        }
        isSearching = false
    }
}
