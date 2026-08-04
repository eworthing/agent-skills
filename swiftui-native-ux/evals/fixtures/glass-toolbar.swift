import SwiftUI

/// Floating control bar over a map. Glass belongs on controls and navigation
/// surfaces — this is a toolbar, not content.
struct MapControlBar: View {
    @Binding var tracking: Bool
    var onLayers: () -> Void

    var body: some View {
        HStack(spacing: 20) {
            Button { tracking.toggle() } label: {
                Label("Follow my location", systemImage: tracking ? "location.fill" : "location")
            }
            Button(action: onLayers) {
                Label("Map layers", systemImage: "square.3.layers.3d")
            }
        }
        .labelStyle(.iconOnly)
        .font(.title3)
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .glassEffect(.regular, in: .capsule)
    }
}
