import SwiftUI

/// First-run onboarding, shown once before any task surface. Not an in-app
/// workflow screen — a large lead visual is the platform norm here, as in
/// Apple's own onboarding and "what's new" sheets.
struct WelcomeView: View {
    @ScaledMetric(relativeTo: .largeTitle) private var symbolSize: CGFloat = 72
    var onContinue: () -> Void

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                Image(systemName: "square.stack.3d.up.fill")
                    .font(.system(size: symbolSize))
                    .foregroundStyle(.tint)
                    .accessibilityHidden(true)

                Text("Welcome to Tierlist")
                    .font(.largeTitle.bold())
                    .multilineTextAlignment(.center)

                Text("Rank anything. Share the result.")
                    .font(.body)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
            }
            .frame(maxWidth: .infinity)
            .padding(24)
        }
        .safeAreaInset(edge: .bottom) {
            Button("Continue", action: onContinue)
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
                .padding(.horizontal, 24)
                .padding(.bottom, 24)
        }
    }
}
