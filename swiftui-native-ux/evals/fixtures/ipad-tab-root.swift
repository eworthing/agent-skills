import SwiftUI

/// iPad root, regular width.
struct LibraryRootView: View {
    let collections: [Collection]

    var body: some View {
        TabView {
            Tab("Library", systemImage: "books.vertical") {
                NavigationStack {
                    List(collections) { collection in
                        NavigationLink(collection.name, value: collection)
                    }
                    .navigationTitle("Library")
                    .navigationDestination(for: Collection.self) {
                        CollectionDetail(collection: $0)
                    }
                }
            }
            Tab("Search", systemImage: "magnifyingglass") {
                NavigationStack { SearchView() }
            }
        }
    }
}
