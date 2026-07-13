import XCTest

@testable import DashboardKit

final class DashboardSummaryTests: XCTestCase {
    func testRenderLinesForKnownSamples() {
        let summary = DashboardSummary(samples: [
            .init(label: "a", value: 2),
            .init(label: "b", value: 4),
            .init(label: "c", value: 6),
        ])
        XCTAssertEqual(summary.render(), [
            "Total 12.00 across 3 samples",
            "Mean 4.00",
            "Peak 6.00",
        ])
    }

    func testSpikyDistributionAppendsWarning() {
        let summary = DashboardSummary(samples: [
            .init(label: "a", value: 1),
            .init(label: "b", value: 1),
            .init(label: "spike", value: 40),
        ])
        XCTAssertEqual(summary.render().last, "Warning: spiky distribution")
    }

    func testEmptySamplesRenderZeroes() {
        let summary = DashboardSummary(samples: [])
        XCTAssertEqual(summary.render(), [
            "Total 0.00 across 0 samples",
            "Mean 0.00",
            "Peak 0.00",
        ])
    }
}
