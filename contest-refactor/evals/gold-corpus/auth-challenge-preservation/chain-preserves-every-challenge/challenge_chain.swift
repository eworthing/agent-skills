// Tries a list of authenticators in order against a supplied credential.
// A rejection reports the challenge from every authenticator that was
// tried, in order, so the caller can see every way it could authenticate.

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
    var challenges: [Challenge] = []
    for authenticator in authenticators {
        if let identity = authenticator.verify(credential) {
            return .authenticated(identity)
        }
        challenges.append(authenticator.challenge)
    }
    return .rejected(challenges: challenges)
}
