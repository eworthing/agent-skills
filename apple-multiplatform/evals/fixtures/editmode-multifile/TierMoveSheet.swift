import SwiftUI

struct TierMoveSheet: View {
    @Bindable var app: AppState

    var body: some View {
        VStack(spacing: 16) {
            Text(title)
            ForEach(allTiers, id: \.self) { tier in
                Button(tier) { app.moveSelection(to: tier) }
                    .focused($focusedTier, equals: tier)
            }
        }
        .onAppear { focusedTier = defaultFocusTier }
        #if os(tvOS)
            .onExitCommand { dismiss() }
        #endif
    }

    // MARK: Private

    @Environment(\.dismiss) private var dismiss
    #if os(iOS) || os(tvOS)
        @Environment(\.editMode) private var editMode
    #endif
    @FocusState private var focusedTier: String?

    private var isBatchMode: Bool {
        app.batchQuickMoveActive
    }

    private var allTiers: [String] {
        app.tierOrder + ["unranked"]
    }

    private var title: String {
        isBatchMode ? "\(app.selection.count) Items" : "Move Item"
    }

    private var defaultFocusTier: String? {
        #if os(iOS) || os(tvOS)
            if let editMode, editMode.wrappedValue == .active, !isBatchMode {
                return allTiers.first
            }
        #endif

        if isBatchMode {
            return allTiers.first
        }
        return app.currentTier(of: app.quickMoveTarget?.id ?? "")
    }
}
