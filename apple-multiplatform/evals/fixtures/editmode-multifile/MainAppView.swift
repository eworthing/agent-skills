import SwiftUI

struct MainAppView: View {
    @Environment(AppState.self) var app: AppState

    #if os(iOS) || os(tvOS)
        @State var editMode: EditMode = .inactive
    #endif

    @Namespace private var glassNamespace
    @State private var focusedCardId: String?

    var body: some View {
        @Bindable var app = app
        let modalBlockingFocus = app.blocksBackgroundFocus

        platformContent(modalBlockingFocus: modalBlockingFocus)
        #if os(iOS) || os(tvOS)
            .environment(\.editMode, $editMode)
        #endif
        #if os(tvOS)
        .task { FocusUtils.seedFocus() }
        #endif
    }

    private func platformContent(modalBlockingFocus: Bool) -> some View {
        gridStack
            .overlay(alignment: .top) {
                #if os(tvOS)
                    TVToolbarView(
                        app: app,
                        modalActive: modalBlockingFocus,
                        editMode: $editMode,
                        glassNamespace: glassNamespace,
                        gridCardFocus: $focusedCardId
                    )
                #endif
            }
            .overlay(alignment: .bottom) {
                #if os(tvOS)
                    TVActionBar(app: app, glassNamespace: glassNamespace)
                        .environment(\.editMode, $editMode)
                        .allowsHitTesting(!modalBlockingFocus)
                        .focusSection()
                #endif
            }
    }

    private var gridStack: some View {
        TierGridView(tierOrder: app.tierOrder)
            .environment(app)
        #if os(iOS)
            .environment(\.editMode, $editMode)
            .padding(.top, Metrics.grid * 2)
        #endif
    }
}
