import SwiftUI

struct PlayerToolbarScreen: View {
    var body: some View {
        NavigationStack {
            ContentView()
                .toolbar {
                    ToolbarItem(placement: .primaryAction) {
                        Button("Cast") { }
                            .buttonStyle(.glass)
                    }
                    ToolbarItem(placement: .secondaryAction) {
                        Button("Settings") { }
                            .buttonStyle(.glassProminent)
                    }
                }
        }
    }
}

struct ContentView: View {
    var body: some View {
        ScrollView {
            LazyVStack { }
        }
    }
}
