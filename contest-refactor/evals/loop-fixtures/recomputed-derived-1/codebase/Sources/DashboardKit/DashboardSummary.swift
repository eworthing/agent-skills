import Foundation

/// Renders a metrics dashboard summary block from a set of samples.
public struct DashboardSummary: Equatable {
    public struct Sample: Equatable {
        public let label: String
        public let value: Double

        public init(label: String, value: Double) {
            self.label = label
            self.value = value
        }
    }

    public struct Statistics: Equatable {
        public let total: Double
        public let mean: Double
        public let peak: Double

        public init(total: Double, mean: Double, peak: Double) {
            self.total = total
            self.mean = mean
            self.peak = peak
        }
    }

    public let samples: [Sample]

    public init(samples: [Sample]) {
        self.samples = samples
    }

    /// Aggregate statistics over `samples`. A pure O(n) derivation of `samples`.
    public var statistics: Statistics {
        let values = samples.map(\.value)
        let total = values.reduce(0, +)
        let mean = values.isEmpty ? 0 : total / Double(values.count)
        let peak = values.max() ?? 0
        return Statistics(total: total, mean: mean, peak: peak)
    }

    public var headline: String { "Total \(Self.format(statistics.total)) across \(samples.count) samples" }
    public var meanLine: String { "Mean \(Self.format(statistics.mean))" }
    public var peakLine: String { "Peak \(Self.format(statistics.peak))" }

    /// Renders the summary block, one line per metric.
    public func render() -> [String] {
        [headline, meanLine, peakLine]
    }

    private static func format(_ value: Double) -> String {
        String(format: "%.2f", value)
    }
}
