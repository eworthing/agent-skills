import Foundation

struct Roster {
    let ids: [UUID]

    init(ids: [UUID]) {
        guard Set(ids).count == ids.count else {
            fatalError("duplicate ids")
        }
        self.ids = ids
    }
}
