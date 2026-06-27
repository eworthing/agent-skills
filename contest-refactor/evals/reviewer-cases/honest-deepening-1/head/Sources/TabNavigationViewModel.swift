import Foundation
import Combine

@MainActor
final class TabNavigationViewModel: ObservableObject {
    @Published private(set) var currentTab: Int = 0

    // Single authority: all callers use this entry point
    func navigateTo(_ tab: Int) {
        currentTab = tab
    }
}
