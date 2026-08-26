// Stores one login per kind (an account may be logged in through more
// than one kind at once -- a primary login and a secondary one, say --
// and each is stored independently).
//
// Storing a login is a single, indivisible write: `commitStore` reads
// current storage and writes the result back in one step. `beginStore`
// only bundles the kind and value together for that call.

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
