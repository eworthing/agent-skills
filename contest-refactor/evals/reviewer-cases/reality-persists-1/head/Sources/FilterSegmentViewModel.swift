import Foundation
import Combine

@MainActor
final class FilterSegmentViewModel: ObservableObject {
    @Published var selectedSegment: Int = 0

    func selectSegment(_ segment: Int) {
        // Log for analytics
        print("[FilterSegment] user selected segment \(segment)")
        selectedSegment = segment   // first writer still present
    }

    func resetToDefault() {
        selectedSegment = 0         // second writer still present
    }
}
