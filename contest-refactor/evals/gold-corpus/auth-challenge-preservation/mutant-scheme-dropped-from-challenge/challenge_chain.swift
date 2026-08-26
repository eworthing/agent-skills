// Tries a list of authenticators in order against a supplied credential,
// recording a challenge alongside each rejected attempt.

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
        challenges.append(Challenge(scheme: "", parameter: authenticator.challenge.parameter))
    }
    return .rejected(challenges: challenges)
}
