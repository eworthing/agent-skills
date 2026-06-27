import Foundation

/// Thin wrapper over UserRepository. Forwards all calls with no added policy,
/// failure isolation, or Locality. Introduced as a boundary-rule sidecar.
final class UserRepositoryWrapper {
    private let repository: UserRepository

    init(repository: UserRepository) {
        self.repository = repository
    }

    func fetchUser(id: String) async -> User? {
        await repository.fetchUser(id: id)
    }

    func saveUser(_ user: User) async {
        await repository.saveUser(user)
    }
}
