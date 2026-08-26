// Authenticates a supplied credential against each account's own stored
// password: the two must match exactly. A request that carries no
// credential at all never authenticates -- there is no account's
// stored password to compare against when nothing was supplied.

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
        guard let stored = storedPasswords[credential.username] else {
            return nil
        }
        return stored == credential.password ? credential.username : nil
    }
}
