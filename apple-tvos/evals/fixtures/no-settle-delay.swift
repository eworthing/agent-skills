import SwiftUI

struct ShowCard: View {
    let show: Show
    @FocusState private var isFocused: Bool
    @State private var previewPlaying = false

    var body: some View {
        Button { } label: {
            ZStack {
                Image(show.poster).resizable().scaledToFill()
                if previewPlaying {
                    VideoPlayerLayer(url: show.previewURL)
                }
            }
            .frame(width: 320, height: 480)
        }
        .buttonStyle(.card)
        .focused($isFocused)
        .onChange(of: isFocused) { _, newValue in
            previewPlaying = newValue
        }
    }
}

struct VideoPlayerLayer: View {
    let url: URL
    var body: some View { Color.black }
}

struct Show: Identifiable, Hashable {
    let id: UUID
    let poster: String
    let previewURL: URL
}
