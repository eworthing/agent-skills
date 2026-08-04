import SwiftUI

struct StatsDashboard: View {
    let stats: [Stat]

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [.purple, .blue, .pink],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()

            ScrollView {
                LazyVGrid(
                    columns: [GridItem(.flexible()), GridItem(.flexible())],
                    spacing: 14
                ) {
                    ForEach(stats) { stat in
                        VStack(alignment: .leading, spacing: 6) {
                            Text(stat.title)
                                .font(.system(size: 11))
                                .fontWeight(.thin)
                                .foregroundStyle(.white.opacity(0.7))
                            Text(stat.value)
                                .font(.system(size: 26, weight: .light))
                                .foregroundStyle(.white)
                        }
                        .frame(maxWidth: .infinity, minHeight: 96, alignment: .leading)
                        .padding(15)
                        .glassEffect(.regular, in: .rect(cornerRadius: 18))
                    }
                }
                .padding(11)
            }
            .background(.ultraThinMaterial)
        }
    }
}
