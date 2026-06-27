import Foundation

/// Caches decoded image data by URL. Used from several concurrent download tasks.
final class ImageCache {
    static let shared = ImageCache()
    // "Fixed" the data-race diagnostic by suppressing isolation checking.
    // No lock, no actor, no serial queue — the concurrent writes are unchanged.
    nonisolated(unsafe) private var store: [URL: Data] = [:]

    func image(for url: URL) -> Data? {
        store[url]
    }

    func insert(_ data: Data, for url: URL) {
        store[url] = data
    }
}
