import Foundation

/// URL endpoint constants for the CMS v2 API. Single site of knowledge for
/// the host, path prefix, and per-endpoint query-parameter defaults.
private enum CMSEndpoint {
    static let base = "https://cms.example.com/api/v2"

    // swiftlint:disable:next line_length
    static let latestArticles = URL(string: "\(base)/articles?sort=published_at&order=desc&per_page=20&fields=title,summary,author,published_at")!

    static func article(id: String) -> URL {
        URL(string: "\(base)/articles/\(id)")!
    }

    static func search(query: String) -> URL {
        URL(string: "\(base)/articles/search?q=\(query)&per_page=20")!
    }
}

/// Loads articles from the remote CMS API.
final class ArticleLoader {
    private let session = URLSession.shared

    func fetchLatest() async throws -> Data {
        let (data, _) = try await session.data(from: CMSEndpoint.latestArticles)
        return data
    }

    func fetchArticle(id: String) async throws -> Data {
        let (data, _) = try await session.data(from: CMSEndpoint.article(id: id))
        return data
    }

    func search(query: String) async throws -> Data {
        let (data, _) = try await session.data(from: CMSEndpoint.search(query: query))
        return data
    }
}
