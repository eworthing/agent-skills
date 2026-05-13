import SwiftUI

struct FeaturedCarousel: View {
    let items: [FeatureItem]
    @FocusState private var focusedID: FeatureItem.ID?

    var body: some View {
        ScrollView(.horizontal) {
            LazyHStack(spacing: 0) {
                ForEach(items) { item in
                    FeatureBanner(item: item)
                        .focused($focusedID, equals: item.id)
                        .containerRelativeFrame(.horizontal)
                }
            }
            .scrollTargetLayout()
        }
        .scrollTargetBehavior(.paging)
    }
}

struct FeatureBanner: View {
    let item: FeatureItem
    var body: some View {
        VStack {
            Image(item.image).resizable().scaledToFit()
            Text(item.title).font(.largeTitle)
        }
    }
}

struct FeatureItem: Identifiable, Hashable {
    let id: UUID
    let title: String
    let image: String
}
