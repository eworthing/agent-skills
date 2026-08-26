// Tries a list of authenticators in order against a supplied credential.
// Keeps track of the challenge for whichever authenticator is currently
// being tried, so a rejection always has a challenge ready to report.

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
    var lastChallenge: Challenge?
    for authenticator in authenticators {
        if let identity = authenticator.verify(credential) {
            return .authenticated(identity)
        }
        lastChallenge = authenticator.challenge
    }
    return .rejected(challenges: lastChallenge.map { [$0] } ?? [])
}
