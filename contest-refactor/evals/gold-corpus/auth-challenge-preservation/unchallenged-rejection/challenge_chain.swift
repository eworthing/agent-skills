// Tries a list of authenticators in order against a supplied credential
// and reports either the identity that verified it or a rejection.

struct Challenge: Equatable {
    let scheme: String
    let parameter: String
}

enum AuthOutcome: Equatable {
    case authenticated(String)
    case rejected(challenges: [Challenge])
}

struct Authenticator {
    let scheme: String
    let parameter: String
    let verify: (String?) -> String?

    var challenge: Challenge { Challenge(scheme: scheme, parameter: parameter) }
}

func authenticateChain(_ authenticators: [Authenticator], credential: String?) -> AuthOutcome {
    for authenticator in authenticators {
        if let identity = authenticator.verify(credential) {
            return .authenticated(identity)
        }
    }
    return .rejected(challenges: [])
}
