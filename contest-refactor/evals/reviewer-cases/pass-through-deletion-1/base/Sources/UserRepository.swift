import Foundation

struct User: Sendable {
    let id: String
    let name: String
    let email: String
}

/// Owns all reads from and writes to the user data store.
actor UserRepository {
    private var store: [String: User] = [:]

    func fetchUser(id: String) async -> User? {
        store[id]
    }

    func saveUser(_ user: User) async {
        store[user.id] = user
    }
}
