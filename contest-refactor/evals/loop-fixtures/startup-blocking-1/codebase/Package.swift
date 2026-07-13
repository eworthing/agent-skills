// swift-tools-version:5.10
import PackageDescription

let package = Package(
    name: "boot",
    products: [
        .library(name: "BootKit", targets: ["BootKit"]),
        .executable(name: "boot", targets: ["boot"]),
    ],
    targets: [
        .target(name: "BootKit"),
        .executableTarget(name: "boot", dependencies: ["BootKit"]),
        .testTarget(name: "BootKitTests", dependencies: ["BootKit"]),
    ]
)
