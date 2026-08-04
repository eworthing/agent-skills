import SwiftUI

// DESIGN TRADEOFF — approved by product 2026-07-20, revisit if TabView gains
// non-Tab content hosting.
//
// This screen ships a custom bar instead of TabView because it is a live game
// HUD: the bar must stay visible through a full-screen drag session, animate
// its height with the drag, and host a running score readout. TabView was
// prototyped first and rejected — it dismisses on drag and cannot host
// non-Tab content. Accessibility parity with a real tab bar is maintained
// explicitly below (selection traits + labelled controls).
struct GameHUDBar: View {
    @Binding var selection: HUDSection
    let score: Int

    var body: some View {
        HStack(spacing: 0) {
            ForEach(HUDSection.allCases) { section in
                Button { selection = section } label: {
                    Label(section.title, systemImage: section.symbol)
                        .frame(maxWidth: .infinity)
                }
                .accessibilityAddTraits(selection == section ? [.isSelected] : [])
            }
        }
        .overlay(alignment: .trailing) {
            Text(score, format: .number)
                .monospacedDigit()
                .accessibilityLabel("Score")
                .padding(.trailing)
        }
    }
}
