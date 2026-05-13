import SwiftUI

struct GameLobby: View {
    @FocusState private var defaultFocus: Bool

    var body: some View {
        VStack(spacing: 40) {
            Text("Choose a Game").font(.largeTitle)
            HStack(spacing: 32) {
                GameTile(title: "Solitaire")
                GameTile(title: "Hearts")
                GameTile(title: "Chess")
            }
            Rectangle()
                .fill(.clear)
                .frame(width: 1, height: 1)
                .focusable()
                .focused($defaultFocus)
                .accessibilityAddTraits(.isButton)
        }
        .onAppear { defaultFocus = true }
    }
}

struct GameTile: View {
    let title: String
    var body: some View {
        Button(title) { }
            .buttonStyle(.bordered)
            .frame(width: 240, height: 160)
    }
}
