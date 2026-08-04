import SwiftUI

/// iPad, regular width. A browsable media collection — grids are the native
/// shape for image content on iPad (Photos, Files icon view, Music albums).
struct LibraryGridView: View {
    let assets: [Asset]

    private let columns = [GridItem(.adaptive(minimum: 160), spacing: 16)]

    var body: some View {
        ScrollView {
            LazyVGrid(columns: columns, spacing: 16) {
                ForEach(assets) { asset in
                    NavigationLink(value: asset) {
                        AssetThumbnail(asset: asset)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(16)
        }
        .navigationTitle("Library")
        .navigationDestination(for: Asset.self) { AssetDetail(asset: $0) }
    }
}
