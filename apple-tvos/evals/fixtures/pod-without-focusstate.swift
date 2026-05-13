import SwiftUI

struct ChannelGrid: View {
    let channels: [Channel]
    let columns = [GridItem(.adaptive(minimum: 280), spacing: 24)]

    var body: some View {
        LazyVGrid(columns: columns, spacing: 24) {
            ForEach(channels) { channel in
                ChannelTile(channel: channel)
                    .focusable()
            }
        }
        .padding(40)
    }
}

struct ChannelTile: View {
    let channel: Channel
    var body: some View {
        VStack(alignment: .leading) {
            Image(channel.logo).resizable().scaledToFit()
            Text(channel.name).font(.title3.weight(.semibold))
        }
        .frame(width: 280, height: 200)
    }
}

struct Channel: Identifiable, Hashable {
    let id: UUID
    let name: String
    let logo: String
}
