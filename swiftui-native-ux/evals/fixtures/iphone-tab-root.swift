import SwiftUI

/// iPhone root. Three flat, co-equal top-level sections — TabView is the
/// native container for exactly this topology.
struct RootView: View {
    var body: some View {
        TabView {
            Tab("Lists", systemImage: "list.bullet") {
                NavigationStack { ListsView() }
            }
            Tab("Browse", systemImage: "square.grid.2x2") {
                NavigationStack { BrowseView() }
            }
            Tab("Settings", systemImage: "gear") {
                NavigationStack { SettingsView() }
            }
        }
    }
}
