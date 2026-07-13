// swift-tools-version:5.10
import PackageDescription

let package = Package(
    name: "HubKit",
    products: [
        .library(name: "HubKit", targets: ["HubKit"]),
        .executable(name: "hub", targets: ["hub"]),
    ],
    targets: [
        .target(name: "HubKit"),
        .executableTarget(name: "hub", dependencies: ["HubKit"]),
        .testTarget(name: "HubKitTests", dependencies: ["HubKit"]),
    ]
)
