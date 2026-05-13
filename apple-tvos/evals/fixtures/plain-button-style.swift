import SwiftUI

struct CategoryGrid: View {
    let categories: [Category]
    @FocusState private var focusedID: Category.ID?

    var body: some View {
        ScrollView(.horizontal) {
            LazyHStack(spacing: 32) {
                ForEach(categories) { category in
                    Button {
                        open(category)
                    } label: {
                        HStack(spacing: 12) {
                            Image(systemName: category.iconName)
                            Text(category.name).font(.headline)
                        }
                        .padding(.horizontal, 28)
                        .padding(.vertical, 18)
                        .background(.regularMaterial, in: .rect(cornerRadius: 14))
                    }
                    .buttonStyle(.plain)
                    .focused($focusedID, equals: category.id)
                }
            }
            .padding(.horizontal, 60)
            .padding(.vertical, 16)
        }
    }

    private func open(_ category: Category) { }
}

struct Category: Identifiable, Hashable {
    let id: UUID
    let name: String
    let iconName: String
}
