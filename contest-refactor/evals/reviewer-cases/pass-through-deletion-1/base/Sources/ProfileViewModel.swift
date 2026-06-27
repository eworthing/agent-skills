import Foundation

@MainActor
final class ProfileViewModel: ObservableObject {
    @Published var user: User?
    private let userRepository: UserRepositoryWrapper

    init(userRepository: UserRepositoryWrapper) {
        self.userRepository = userRepository
    }

    func loadProfile(id: String) async {
        user = await userRepository.fetchUser(id: id)
    }

    func updateProfile(_ user: User) async {
        await userRepository.saveUser(user)
        self.user = user
    }
}
