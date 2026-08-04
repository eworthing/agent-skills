import SwiftUI

struct TierRow: View {
    let item: Item
    let rank: Int
    var onReorder: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            Text("\(rank)")
                .font(.headline)
                .frame(width: 28)

            VStack(alignment: .leading) {
                Text(item.title).font(.body)
                Text(item.subtitle).font(.caption).foregroundStyle(.secondary)
            }

            Spacer()

            Button(action: onReorder) {
                Image(systemName: "arrow.up.arrow.down")
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(
            "Rank \(rank), \(item.title), \(item.subtitle), double tap the reorder button to move this item"
        )
    }
}
