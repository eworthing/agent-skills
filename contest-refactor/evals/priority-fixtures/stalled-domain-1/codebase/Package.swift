// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "BookingKit",
    platforms: [.macOS(.v13), .iOS(.v16)],
    products: [
        .library(name: "BookingKit", targets: ["BookingKit"])
    ],
    targets: [
        .target(name: "BookingKit"),
        .testTarget(name: "BookingKitTests", dependencies: ["BookingKit"]),
    ]
)
