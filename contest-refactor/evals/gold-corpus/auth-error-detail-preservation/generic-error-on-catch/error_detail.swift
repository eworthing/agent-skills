// Middleware that runs a guarded operation and, if it raises, rethrows a
// fresh failure of its own rather than the original.

struct SourceLocation: Equatable, CustomStringConvertible {
    let file: String
    let line: Int
    var description: String { "\(file):\(line)" }
}

struct AuthFailure: Error, Equatable {
    let reason: String
    let challenge: String
    let identifier: String
    let source: SourceLocation
}

/// The original site where an authentication failure is raised.
func rejectMissingCredential() -> AuthFailure {
    AuthFailure(
        reason: "no credential was supplied",
        challenge: "vault-token",
        identifier: "auth.credential.missing",
        source: SourceLocation(file: "vault_gate.swift", line: 42)
    )
}

/// A caller downstream of the middleware inspects whatever it catches
/// through this protocol -- conformers report whichever of the four
/// pieces they actually carry, nil for anything they don't.
protocol RethrownDetail: Error {
    var recoveredReason: String? { get }
    var recoveredChallenge: String? { get }
    var recoveredIdentifier: String? { get }
    var recoveredSource: SourceLocation? { get }
}

extension AuthFailure: RethrownDetail {
    var recoveredReason: String? { reason }
    var recoveredChallenge: String? { challenge }
    var recoveredIdentifier: String? { identifier }
    var recoveredSource: SourceLocation? { source }
}

struct GenericFailure: Error {}

func withErrorMiddleware(_ operation: () throws -> String) throws -> String {
    do {
        return try operation()
    } catch {
        throw GenericFailure()
    }
}
