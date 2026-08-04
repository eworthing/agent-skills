import SwiftUI

/// Floating control bar over a map. Glass belongs on controls and navigation
/// surfaces — this is a toolbar, not content.
struct MapControlBar: View {
    @Binding var tracking: Bool
    var onLayers: () -> Void

    var body: some View {
        HStack(spacing: 4) {
            Toggle(isOn: $tracking) {
                Label(
                    "Follow my location",
                    systemImage: tracking ? "location.fill" : "location"
                )
                .frame(minWidth: 44, minHeight: 44)
            }
            .toggleStyle(.button)

            Button(action: onLayers) {
                Label("Map layers", systemImage: "square.3.layers.3d")
                    .frame(minWidth: 44, minHeight: 44)
            }
        }
        .labelStyle(.iconOnly)
        .font(.title3)
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .glassEffect(.regular, in: .capsule)
    }
}
