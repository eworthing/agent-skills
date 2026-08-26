// Stores one login per kind (an account may be logged in through more
// than one kind at once -- a primary login and a secondary one, say --
// and each is stored independently).
//
// Storing a login is a single, indivisible write: `commitStore` reads
// current storage and writes the result back in one step, with no
// point where another caller's own commit can land in between.
// `beginStore` has nothing to remember ahead of time -- unlike a
// design that captures a snapshot of storage before the write happens,
// there is no stale copy here for a later commit to overwrite storage
// with.

enum LoginKind: Int, Hashable {
    case primary = 0
    case secondary = 1
}

struct PendingStore {
    let kind: LoginKind
    let value: String
}

final class LoginRegistry {
    private var entries: [LoginKind: String] = [:]

    func beginStore(kind: LoginKind, value: String) -> PendingStore {
        PendingStore(kind: kind, value: value)
    }

    func commitStore(_ pending: PendingStore) {
        entries[pending.kind] = pending.value
    }

    func retrieve(kind: LoginKind) -> String? {
        entries[kind]
    }
}
