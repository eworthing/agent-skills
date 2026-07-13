import DashboardKit

let summary = DashboardSummary(samples: [
    .init(label: "requests", value: 120),
    .init(label: "errors", value: 4),
    .init(label: "latency", value: 38),
])
for line in summary.render() {
    print(line)
}

let formatter = UnitFormatter(unit: "ms")
for line in formatter.format([12, 8, 30]) {
    print(line)
}
