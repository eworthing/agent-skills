// swift-tools-version:5.10
import PackageDescription

let package = Package(
    name: "FeedKit",
    products: [
        .library(name: "FeedKit", targets: ["FeedKit"]),
        .executable(name: "feed", targets: ["feed"]),
    ],
    targets: [
        .target(name: "FeedKit"),
        .executableTarget(name: "feed", dependencies: ["FeedKit"]),
        .testTarget(name: "FeedKitTests", dependencies: ["FeedKit"]),
    ]
)
