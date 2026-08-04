import SwiftUI

/// Ported from the React marketing dashboard. iPhone.
struct ProjectsScreen: View {
    @State private var showMenu = false
    let projects: [Project]

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Button { showMenu.toggle() } label: {
                    Image(systemName: "line.3.horizontal")
                }
                Spacer()
                Text("Projects").font(.system(size: 17, weight: .semibold))
                Spacer()
                Image(systemName: "bell")
            }
            .padding(.horizontal, 15)
            .frame(height: 56)

            ScrollView {
                VStack(spacing: 8) {
                    Text("Ship faster.")
                        .font(.system(size: 34, weight: .bold))
                    Text("Everything your team needs in one place.")
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, minHeight: 220)
                .background(
                    LinearGradient(
                        colors: [.indigo.opacity(0.3), .clear],
                        startPoint: .top,
                        endPoint: .bottom
                    )
                )

                HStack(alignment: .top, spacing: 12) {
                    LazyVGrid(
                        columns: [GridItem(.flexible()), GridItem(.flexible())],
                        spacing: 12
                    ) {
                        ForEach(projects) { ProjectCard(project: $0) }
                    }

                    VStack(alignment: .leading, spacing: 10) {
                        Text("AI Assistant")
                            .font(.system(size: 13, weight: .semibold))
                        Text("Ask anything about your projects")
                            .font(.system(size: 11))
                            .foregroundStyle(.secondary)
                    }
                    .frame(width: 220)
                    .padding(15)
                    .background(.regularMaterial, in: .rect(cornerRadius: 12))
                }
                .padding(15)
            }
        }
        .sheet(isPresented: $showMenu) { SideMenu() }
    }
}
