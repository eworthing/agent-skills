import Foundation

@MainActor
final class SettingsViewModel: ObservableObject {
    @Published var settings = AppSettings(themeMode: "system", notificationsEnabled: true, fontSize: 16)
    private let store: SettingsStore

    init(store: SettingsStore) {
        self.store = store
    }

    func load() async {
        settings = await store.current
    }

    func save() async {
        await store.update(settings)
    }

    func applyTheme(_ mode: String) async {
        await store.updateTheme(mode)
        settings.themeMode = mode
    }
}
