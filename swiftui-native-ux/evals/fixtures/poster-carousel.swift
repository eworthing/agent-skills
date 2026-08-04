import SwiftUI

/// Poster carousel. The fixed dimensions constrain the *artwork box*. The
/// caption shares the column width but is never height-capped nor line-limited,
/// so it wraps and grows with Dynamic Type rather than truncating.
struct PosterCarousel: View {
    let posters: [Poster]

    private let artworkWidth: CGFloat = 120

    var body: some View {
        ScrollView(.horizontal) {
            LazyHStack(alignment: .top, spacing: 12) {
                ForEach(posters) { poster in
                    VStack(alignment: .leading, spacing: 6) {
                        AsyncImage(url: poster.artworkURL) { image in
                            image.resizable().aspectRatio(2 / 3, contentMode: .fill)
                        } placeholder: {
                            Rectangle().fill(.quaternary)
                        }
                        .frame(width: artworkWidth, height: artworkWidth * 1.5)
                        .clipShape(.rect(cornerRadius: 8))

                        Text(poster.title)
                            .font(.caption)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    .frame(width: artworkWidth, alignment: .leading)
                }
            }
            .padding(.horizontal, 16)
        }
        .scrollIndicators(.hidden)
    }
}
