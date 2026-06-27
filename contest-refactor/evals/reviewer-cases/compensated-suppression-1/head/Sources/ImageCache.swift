import Foundation

/// Caches decoded image data by URL. Used from several concurrent download tasks.
///
/// `@unchecked Sendable` is sound here because every access to the mutable
/// `store` is serialized by `lock` (the compensating invariant). Verified with
/// ThreadSanitizer over 200 concurrent inserts — see ImageCacheConcurrencyTests.
final class ImageCache: @unchecked Sendable {
    static let shared = ImageCache()
    private let lock = NSLock()
    private var store: [URL: Data] = [:]

    func image(for url: URL) -> Data? {
        lock.withLock { store[url] }
    }

    func insert(_ data: Data, for url: URL) {
        lock.withLock { store[url] = data }
    }
}
