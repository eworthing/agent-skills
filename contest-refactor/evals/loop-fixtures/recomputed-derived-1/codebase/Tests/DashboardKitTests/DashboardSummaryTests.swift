import XCTest

@testable import DashboardKit

final class DashboardSummaryTests: XCTestCase {
    func testStatisticsForKnownSamples() {
        let summary = DashboardSummary(samples: [
            .init(label: "a", value: 2),
            .init(label: "b", value: 4),
            .init(label: "c", value: 6),
        ])
        XCTAssertEqual(summary.statistics, .init(total: 12, mean: 4, peak: 6))
    }

    func testStatisticsForEmptySamples() {
        let summary = DashboardSummary(samples: [])
        XCTAssertEqual(summary.statistics, .init(total: 0, mean: 0, peak: 0))
    }

    func testPeakIsMaximumNotZeroForAllNegativeSamples() {
        let summary = DashboardSummary(samples: [
            .init(label: "a", value: -8),
            .init(label: "b", value: -3),
            .init(label: "c", value: -5),
        ])
        XCTAssertEqual(summary.statistics, .init(total: -16, mean: -16.0 / 3.0, peak: -3))
    }

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

    func testRenderLinesForEmptySamples() {
        let summary = DashboardSummary(samples: [])
        XCTAssertEqual(summary.render(), [
            "Total 0.00 across 0 samples",
            "Mean 0.00",
            "Peak 0.00",
        ])
    }
}

final class UnitFormatterTests: XCTestCase {
    func testFormatAppendsUnitToEveryValue() {
        let formatter = UnitFormatter(unit: "ms")
        XCTAssertEqual(formatter.format([1, 2.5, 30]), ["1.00 ms", "2.50 ms", "30.00 ms"])
    }

    func testFormatEmptyInputIsEmpty() {
        let formatter = UnitFormatter(unit: "ms")
        XCTAssertEqual(formatter.format([]), [])
    }
}
