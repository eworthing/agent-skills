// swift-tools-version:5.10
import PackageDescription

let package = Package(
    name: "DashboardKit",
    products: [
        .library(name: "DashboardKit", targets: ["DashboardKit"]),
        .executable(name: "dashboard", targets: ["dashboard"]),
    ],
    targets: [
        .target(name: "DashboardKit"),
        .executableTarget(name: "dashboard", dependencies: ["DashboardKit"]),
        .testTarget(name: "DashboardKitTests", dependencies: ["DashboardKit"]),
    ]
)
