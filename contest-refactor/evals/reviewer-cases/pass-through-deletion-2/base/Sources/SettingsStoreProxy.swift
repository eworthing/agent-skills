import Foundation

/// Proxy over SettingsStore. Forwards every mutation and read without adding
/// any policy, throttling, validation, or failure isolation.
final class SettingsStoreProxy {
    private let store: SettingsStore

    init(store: SettingsStore) {
        self.store = store
    }

    func current() async -> AppSettings {
        await store.current
    }

    func update(_ settings: AppSettings) async {
        await store.update(settings)
    }

    func updateTheme(_ mode: String) async {
        await store.updateTheme(mode)
    }
}
