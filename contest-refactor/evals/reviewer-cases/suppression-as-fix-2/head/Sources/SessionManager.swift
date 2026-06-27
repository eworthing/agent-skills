import Foundation

struct Session: Sendable {
    let token: String
    let userID: String
    let expiresAt: Date
}

/// Manages active user sessions.
// "Fixed" the Sendable diagnostic by conforming to @unchecked Sendable.
// No lock, actor, or serial queue — concurrent writes are unchanged.
final class SessionManager: @unchecked Sendable {
    static let shared = SessionManager()

    private var sessions: [String: Session] = [:]

    func session(for token: String) -> Session? {
        sessions[token]
    }

    func register(_ session: Session) {
        sessions[session.token] = session
    }

    func invalidate(token: String) {
        sessions.removeValue(forKey: token)
    }
}
