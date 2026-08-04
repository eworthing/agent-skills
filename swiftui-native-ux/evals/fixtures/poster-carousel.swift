import SwiftUI

/// Poster carousel. The fixed height constrains the *artwork box only* — no
/// text lives inside that frame, so Dynamic Type is unaffected. The caption
/// sits outside the constrained frame and grows freely.
struct PosterCarousel: View {
    let posters: [Poster]

    var body: some View {
        ScrollView(.horizontal) {
            LazyHStack(spacing: 12) {
                ForEach(posters) { poster in
                    VStack(alignment: .leading, spacing: 6) {
                        AsyncImage(url: poster.artworkURL) { image in
                            image.resizable().aspectRatio(2 / 3, contentMode: .fill)
                        } placeholder: {
                            Rectangle().fill(.quaternary)
                        }
                        .frame(width: 120, height: 180)
                        .clipShape(.rect(cornerRadius: 8))

                        Text(poster.title)
                            .font(.caption)
                            .lineLimit(2)
                    }
                    .frame(width: 120)
                }
            }
            .padding(.horizontal, 16)
        }
        .scrollIndicators(.hidden)
    }
}
