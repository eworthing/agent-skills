// swift-tools-version:5.10
import PackageDescription

let package = Package(
    name: "HubKit",
    products: [
        .library(name: "HubKit", targets: ["HubKit"])
    ],
    targets: [
        .target(name: "HubKit"),
        .testTarget(name: "HubKitTests", dependencies: ["HubKit"]),
    ]
)
