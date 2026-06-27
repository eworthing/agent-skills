import Foundation
import Combine

@MainActor
final class TabNavigationViewModel: ObservableObject {
    @Published var currentTab: Int = 0

    func userTappedTab(_ index: Int) {
        currentTab = index
    }

    func handleNotification(targetTab: Int) {
        // Second writer — called from push notification handler
        currentTab = targetTab
    }
}
