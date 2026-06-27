import Foundation

/// Caches decoded image data by URL. Used from several concurrent download tasks.
final class ImageCache {
    static let shared = ImageCache()
    private var store: [URL: Data] = [:]

    func image(for url: URL) -> Data? {
        store[url]
    }

    func insert(_ data: Data, for url: URL) {
        // Called from inside `Task { }` sites in the download layer — concurrent
        // writers to `store` with no isolation. This is the targeted race.
        store[url] = data
    }
}
