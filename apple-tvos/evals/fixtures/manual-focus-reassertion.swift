import SwiftUI

struct DetailScreen: View {
    @FocusState private var isPrimaryFocused: Bool
    @State private var showDetail = false

    var body: some View {
        VStack(spacing: 32) {
            Button("Play Now") { }
                .focused($isPrimaryFocused)

            Button("More Info") { showDetail = true }
        }
        .onAppear {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                isPrimaryFocused = true
            }
        }
        .sheet(isPresented: $showDetail) {
            DetailModal()
        }
    }
}

struct DetailModal: View {
    @Environment(\.dismiss) private var dismiss
    var body: some View {
        VStack {
            Text("Detail")
            Button("Close") { dismiss() }
        }
    }
}
