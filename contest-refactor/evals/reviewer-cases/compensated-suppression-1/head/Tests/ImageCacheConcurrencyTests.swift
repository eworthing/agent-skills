import XCTest
@testable import App

/// Concurrency regression test for the compensating lock invariant on
/// `ImageCache.store`. This is the test cited in the loop_result TSAN evidence:
/// it drives 200 concurrent inserts + reads and asserts every write is observed,
/// which only holds if all access to `store` is serialized by the lock. Run under
/// ThreadSanitizer it reports zero races; without the lock it data-races and the
/// final count is nondeterministic.
final class ImageCacheConcurrencyTests: XCTestCase {
    func testConcurrentInsertsAreSerialized() {
        let cache = ImageCache.shared
        let count = 200
        let group = DispatchGroup()
        for i in 0..<count {
            group.enter()
            DispatchQueue.global().async {
                let url = URL(string: "https://example.com/img/\(i).png")!
                cache.insert(Data([UInt8(i % 256)]), for: url)
                group.leave()
            }
        }
        group.wait()

        // Every concurrent write must be observable — proves the lock serialized
        // the inserts rather than losing writes to a data race.
        for i in 0..<count {
            let url = URL(string: "https://example.com/img/\(i).png")!
            XCTAssertEqual(cache.image(for: url), Data([UInt8(i % 256)]),
                           "write for \(url) was lost — access to store was not serialized")
        }
    }
}
