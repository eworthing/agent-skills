// Stores one login per kind (an account may be logged in through more
// than one kind at once -- a primary login and a secondary one, say --
// and each is stored independently). Each kind's storage update is
// guarded by its own lock, so a caller's read-modify-write of storage
// is synchronized before it lands.

enum LoginKind: Int, Hashable {
    case primary = 0
    case secondary = 1
}

/// A trivial mutual-exclusion primitive: acquiring it while it is
/// already held traps, the same way reacquiring a real lock on the
/// same thread would deadlock.
final class Lock {
    private var held = false

    func acquire() {
        precondition(!held, "lock already held")
        held = true
    }

    func release() {
        precondition(held, "lock not held")
        held = false
    }
}

struct PendingStore {
    let kind: LoginKind
    let value: String
    let snapshot: [LoginKind: String]
}

final class LoginRegistry {
    private var entries: [LoginKind: String] = [:]
    private let locksByKind: [LoginKind: Lock] = [.primary: Lock(), .secondary: Lock()]

    func beginStore(kind: LoginKind, value: String) -> PendingStore {
        locksByKind[kind]!.acquire()
        return PendingStore(kind: kind, value: value, snapshot: entries)
    }

    func commitStore(_ pending: PendingStore) {
        var updated = pending.snapshot
        updated[pending.kind] = pending.value
        entries = updated
        locksByKind[pending.kind]!.release()
    }

    func retrieve(kind: LoginKind) -> String? {
        entries[kind]
    }
}
