// Stores one login per kind (an account may be logged in through more
// than one kind at once -- a primary login and a secondary one, say --
// and each is stored independently). Storing a login is split into two
// steps: `beginStore` looks at what is currently stored, and
// `commitStore` writes the result back.

enum LoginKind: Int, Hashable {
    case primary = 0
    case secondary = 1
}

struct PendingStore {
    let kind: LoginKind
    let value: String
    let snapshot: [LoginKind: String]
}

final class LoginRegistry {
    private var entries: [LoginKind: String] = [:]

    func beginStore(kind: LoginKind, value: String) -> PendingStore {
        PendingStore(kind: kind, value: value, snapshot: entries)
    }

    func commitStore(_ pending: PendingStore) {
        var updated = pending.snapshot
        updated[pending.kind] = pending.value
        entries = updated
    }

    func retrieve(kind: LoginKind) -> String? {
        entries[kind]
    }
}
