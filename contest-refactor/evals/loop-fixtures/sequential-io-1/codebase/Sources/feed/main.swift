import FeedKit

let refresher = FeedRefresher { id in
    FeedRefresher.Summary(id: id, itemCount: id.count)
}
let summaries = try await refresher.refreshAll(ids: ["news", "sports", "weather"])
for id in summaries.keys.sorted() {
    print("\(id): \(summaries[id]!.itemCount)")
}
