import SwiftUI

struct LibraryView: View {
    @State private var confirmDelete = false

    var body: some View {
        Button("Delete All", role: .destructive) {
            confirmDelete = true
        }
        .confirmationDialog(
            "Delete All Items?",
            isPresented: $confirmDelete,
            titleVisibility: .visible
        ) {
            Button("Delete All", role: .destructive) { deleteEverything() }
            Button("Cancel", role: .cancel) { }
        } message: {
            Text("This cannot be undone.")
        }
    }

    private func deleteEverything() { }
}
