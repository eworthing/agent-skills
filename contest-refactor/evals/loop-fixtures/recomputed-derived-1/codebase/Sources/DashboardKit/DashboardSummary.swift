import Foundation

/// Renders the metrics dashboard summary block.
struct DashboardSummary {
    struct Sample: Equatable {
        let label: String
        let value: Double
    }

    struct Statistics: Equatable {
        let total: Double
        let mean: Double
        let peak: Double
    }

    let samples: [Sample]

    /// Aggregate statistics over `samples`.
    var statistics: Statistics {
        var total = 0.0
        var peak = 0.0
        for sample in samples {
            total += sample.value
            peak = max(peak, sample.value)
        }
        let mean = samples.isEmpty ? 0 : total / Double(samples.count)
        return Statistics(total: total, mean: mean, peak: peak)
    }

    /// Number of samples in this summary.
    var sampleCount: Int { samples.count }

    var headline: String { "Total \(format(statistics.total)) across \(sampleCount) samples" }
    var meanLine: String { "Mean \(format(statistics.mean))" }
    var peakLine: String { "Peak \(format(statistics.peak))" }

    /// Renders the summary block, one line per row.
    func render() -> [String] {
        var lines = [headline, meanLine, peakLine]
        if sampleCount > 0 && statistics.peak > statistics.mean * 2 {
            lines.append("Warning: spiky distribution")
        }
        return lines
    }

    private func format(_ value: Double) -> String {
        String(format: "%.2f", value)
    }
}
