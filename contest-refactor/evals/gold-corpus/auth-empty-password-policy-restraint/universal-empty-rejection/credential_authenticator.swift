// Authenticates a supplied credential against each account's own stored
// password. An empty password is rejected outright, ahead of any
// per-account check -- a blanket hardening pass against a class of guess
// that looks like it should never be allowed to succeed.

struct Credential {
    let username: String
    let password: String
}

enum SuppliedCredential {
    case none
    case some(Credential)
}

struct Authenticator {
    private let storedPasswords: [String: String]

    init(storedPasswords: [String: String]) {
        self.storedPasswords = storedPasswords
    }

    /// The authenticated username, or nil if `supplied` does not
    /// authenticate.
    func authenticate(_ supplied: SuppliedCredential) -> String? {
        guard case .some(let credential) = supplied else {
            return nil
        }
        guard !credential.password.isEmpty else {
            return nil
        }
        guard let stored = storedPasswords[credential.username] else {
            return nil
        }
        return stored == credential.password ? credential.username : nil
    }
}
