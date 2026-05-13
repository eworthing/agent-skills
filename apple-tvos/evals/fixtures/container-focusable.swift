import SwiftUI

struct CardRow: View {
    let cards: [Card]
    @FocusState private var focusedID: Card.ID?

    var body: some View {
        HStack(spacing: 24) {
            ForEach(cards) { card in
                CardView(card: card)
                    .focused($focusedID, equals: card.id)
            }
        }
        .focusable()
        .padding(.horizontal, 40)
    }
}

struct CardView: View {
    let card: Card
    var body: some View {
        VStack {
            Image(card.imageName)
            Text(card.title)
        }
        .frame(width: 280, height: 360)
        .background(.regularMaterial, in: .rect(cornerRadius: 16))
    }
}

struct Card: Identifiable, Hashable {
    let id: UUID
    let title: String
    let imageName: String
}
