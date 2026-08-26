// Authenticates a supplied credential against each account's own stored
// password. Most accounts require their stored password to match
// exactly. A small number of accounts -- a shared kiosk terminal with no
// individual owner to hold a secret, say -- are deliberately provisioned
// with an empty stored password, and are meant to authenticate with an
// empty one supplied.

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
