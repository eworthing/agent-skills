import SwiftUI

#if os(tvOS)
    struct TVActionBar: View {
        // MARK: Internal

        @Bindable var app: AppState

        var glassNamespace: Namespace.ID

        var body: some View {
            if isMultiSelectActive {
                let hasSelection = !app.selection.isEmpty
                let defaultFocus = hasSelection ? FocusTarget.move : .clear
                HStack(spacing: 20) {
                    Text("\(app.selection.count) Selected")
                        .accessibilityIdentifier("ActionBar_SelectionCount")

                    Spacer()

                    if hasSelection {
                        Button(ActionID.batchMove.label) {
                            app.presentBatchQuickMove()
                        }
                        .buttonStyle(.glassProminent)
                        .focused($focusedControl, equals: .move)
                    }

                    Button(ActionID.clearSelection.label) {
                        app.clearSelection()
                    }
                    .buttonStyle(.glass)
                    .focused($focusedControl, equals: .clear)
                }
                .focusSection()
                .defaultFocus($focusedControl, defaultFocus)
                .onExitCommand {
                    guard editMode != nil else {
                        return
                    }
                    withAnimation(.easeInOut(duration: 0.2)) {
                        editMode?.wrappedValue = .inactive
                        app.clearSelection()
                    }
                }
                .frame(height: TVMetrics.bottomBarHeight)
                .transition(.move(edge: .bottom).combined(with: .opacity))
            }
        }

        // MARK: Private

        private enum FocusTarget: Hashable {
            case move
            case clear
        }

        @Environment(\.editMode) private var editMode
        @FocusState private var focusedControl: FocusTarget?

        private var isMultiSelectActive: Bool {
            editMode?.wrappedValue == .active
        }
    }
#endif
