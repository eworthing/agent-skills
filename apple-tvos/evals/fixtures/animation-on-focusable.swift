import SwiftUI

struct HeroCard: View {
    let title: String
    @State private var highlighted = false

    var body: some View {
        Button {
            highlighted.toggle()
        } label: {
            VStack(spacing: 12) {
                Image(systemName: "play.tv.fill").font(.system(size: 80))
                Text(title).font(.title2)
            }
            .scaleEffect(highlighted ? 1.05 : 1.0)
        }
        .buttonStyle(.card)
        .animation(.spring(response: 0.4, dampingFraction: 0.7), value: highlighted)
    }
}
