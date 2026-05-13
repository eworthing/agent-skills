import SwiftUI

struct LibraryRoot: View {
    @State private var showSettings = false

    var body: some View {
        Button("Settings") { showSettings = true }
            .fullScreenCover(isPresented: $showSettings) {
                SettingsContent()
                    .onExitCommand { showSettings = false }
            }
    }
}

struct SettingsContent: View {
    @FocusState private var focusedField: SettingsField?

    enum SettingsField: Hashable { case account, playback, accessibility }

    var body: some View {
        VStack(spacing: 32) {
            Button("Account") { }.focused($focusedField, equals: .account)
            Button("Playback") { }.focused($focusedField, equals: .playback)
            Button("Accessibility") { }.focused($focusedField, equals: .accessibility)
        }
        .onAppear { focusedField = .account }
    }
}
