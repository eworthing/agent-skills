import SwiftUI

// DESIGN TRADEOFF — approved by product 2026-07-20.
//
// This is a live game HUD section switcher, not app-level navigation, and the
// bar must animate its own height from an in-progress DragGesture. SwiftUI
// exposes no control over the system tab bar's height and no way to drive it
// from a gesture, so TabView cannot express this regardless of styling or
// accessory placement. TabView was prototyped first and rejected on that
// height-control constraint alone.
//
// Accessibility parity with a real tab bar is maintained explicitly below:
// a visible selected state that does not rely on color alone, selection
// traits, and a score exposed as a labelled value.
struct GameHUDBar: View {
    @Binding var selection: HUDSection
    let score: Int

    var body: some View {
        HStack(spacing: 0) {
            ForEach(HUDSection.allCases) { section in
                Button { selection = section } label: {
                    Label(section.title, systemImage: section.symbol)
                        .symbolVariant(selection == section ? .fill : .none)
                        .foregroundStyle(selection == section ? Color.accentColor : Color.secondary)
                        .frame(maxWidth: .infinity, minHeight: 44)
                }
                .accessibilityAddTraits(selection == section ? [.isSelected] : [])
            }

            Text(score, format: .number)
                .monospacedDigit()
                .accessibilityLabel("Score")
                .accessibilityValue(Text(score, format: .number))
                .padding(.horizontal)
        }
    }
}
