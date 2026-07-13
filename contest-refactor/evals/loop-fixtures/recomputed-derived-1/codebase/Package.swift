// swift-tools-version:5.10
import PackageDescription

let package = Package(
    name: "DashboardKit",
    products: [
        .library(name: "DashboardKit", targets: ["DashboardKit"])
    ],
    targets: [
        .target(name: "DashboardKit"),
        .testTarget(name: "DashboardKitTests", dependencies: ["DashboardKit"]),
    ]
)
