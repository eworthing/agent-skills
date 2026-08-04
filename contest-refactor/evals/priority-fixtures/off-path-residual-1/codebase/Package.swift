// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "LedgerKit",
    platforms: [.macOS(.v13), .iOS(.v16)],
    products: [.library(name: "LedgerKit", targets: ["LedgerKit"])],
    targets: [
        .target(name: "LedgerKit"),
        .testTarget(name: "LedgerKitTests", dependencies: ["LedgerKit"]),
    ]
)
