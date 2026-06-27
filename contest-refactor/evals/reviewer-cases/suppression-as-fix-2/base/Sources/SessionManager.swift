import Foundation

struct Session: Sendable {
    let token: String
    let userID: String
    let expiresAt: Date
}

/// Manages active user sessions. Sessions are created and invalidated from
/// URLSession delegate callbacks, which arrive on arbitrary threads.
final class SessionManager {
    static let shared = SessionManager()

    private var sessions: [String: Session] = [:]

    func session(for token: String) -> Session? {
        sessions[token]
    }

    func register(_ session: Session) {
        // Called from URLSession delegate callbacks on background threads —
        // concurrent writers to `sessions` with no isolation.
        sessions[session.token] = session
    }

    func invalidate(token: String) {
        sessions.removeValue(forKey: token)
    }
}
