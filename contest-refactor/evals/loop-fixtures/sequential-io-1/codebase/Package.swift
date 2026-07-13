// swift-tools-version:5.10
import PackageDescription

let package = Package(
    name: "FeedKit",
    products: [
        .library(name: "FeedKit", targets: ["FeedKit"])
    ],
    targets: [
        .target(name: "FeedKit"),
        .testTarget(name: "FeedKitTests", dependencies: ["FeedKit"]),
    ]
)
