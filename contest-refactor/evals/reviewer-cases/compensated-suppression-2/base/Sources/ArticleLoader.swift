import Foundation

/// Loads articles from the remote CMS API. Each method builds its endpoint URL
/// independently — the host, path prefix, and query defaults are duplicated.
final class ArticleLoader {
    private let session = URLSession.shared

    func fetchLatest() async throws -> Data {
        let url = URL(string: "https://cms.example.com/api/v2/articles?sort=published_at&order=desc&per_page=20&fields=title,summary,author,published_at")!
        let (data, _) = try await session.data(from: url)
        return data
    }

    func fetchArticle(id: String) async throws -> Data {
        let url = URL(string: "https://cms.example.com/api/v2/articles/\(id)")!
        let (data, _) = try await session.data(from: url)
        return data
    }

    func search(query: String) async throws -> Data {
        let url = URL(string: "https://cms.example.com/api/v2/articles/search?q=\(query)&per_page=20")!
        let (data, _) = try await session.data(from: url)
        return data
    }
}
