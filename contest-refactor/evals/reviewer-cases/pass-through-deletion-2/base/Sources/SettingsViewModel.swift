import Foundation

@MainActor
final class SettingsViewModel: ObservableObject {
    @Published var settings = AppSettings(themeMode: "system", notificationsEnabled: true, fontSize: 16)
    private let proxy: SettingsStoreProxy

    init(proxy: SettingsStoreProxy) {
        self.proxy = proxy
    }

    func load() async {
        settings = await proxy.current()
    }

    func save() async {
        await proxy.update(settings)
    }

    func applyTheme(_ mode: String) async {
        await proxy.updateTheme(mode)
        settings.themeMode = mode
    }
}
