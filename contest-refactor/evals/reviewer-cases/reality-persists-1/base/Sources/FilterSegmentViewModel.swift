import Foundation
import Combine

@MainActor
final class FilterSegmentViewModel: ObservableObject {
    @Published var selectedSegment: Int = 0

    func applyFilter(_ segment: Int) {
        selectedSegment = segment
    }

    func resetToDefault() {
        selectedSegment = 0
    }
}
