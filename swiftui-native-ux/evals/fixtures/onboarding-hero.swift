import SwiftUI

/// First-run onboarding, shown once before any task surface. Not an in-app
/// workflow screen — a large lead visual is the platform norm here, as in
/// Apple's own onboarding and "what's new" sheets.
struct WelcomeView: View {
    var onContinue: () -> Void

    var body: some View {
        VStack(spacing: 24) {
            Image(systemName: "square.stack.3d.up.fill")
                .font(.system(size: 72))
                .foregroundStyle(.tint)
                .accessibilityHidden(true)

            Text("Welcome to Tierlist")
                .font(.largeTitle.bold())
                .multilineTextAlignment(.center)

            Text("Rank anything. Share the result.")
                .font(.body)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)

            Spacer()

            Button("Continue", action: onContinue)
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
        }
        .padding(24)
    }
}
