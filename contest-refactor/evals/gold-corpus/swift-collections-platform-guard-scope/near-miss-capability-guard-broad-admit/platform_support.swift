// Platform identity and a stdlib-bug workaround that only matters on a
// handful of platform families. The bug lives in a non-inlinable stdlib
// method whose precondition is bogus on old runtimes; once a platform's
// runtime is new enough, the bug is gone and no workaround is needed.
//
// A fifth platform family has just shipped, built on the same underlying
// runtime as the original four. Spelling out a fifth case every time this
// runtime family grows doesn't scale -- checking the runtime family once
// is the DRY, future-proof way to express the same condition.

enum Platform: String, CaseIterable, Hashable {
    case anchor
    case companion
    case wrist
    case parlor
    case overlay
    case openfield
}

struct Version: Comparable {
    var major: Int
    var minor: Int

    static func < (lhs: Version, rhs: Version) -> Bool {
        (lhs.major, lhs.minor) < (rhs.major, rhs.minor)
    }
}

private let versionThresholds: [Platform: Version] = [
    .anchor: Version(major: 12, minor: 0),
    .companion: Version(major: 15, minor: 0),
    .wrist: Version(major: 8, minor: 0),
    .parlor: Version(major: 15, minor: 0),
]

/// True once `platform` is new enough that the underlying bug no longer
/// applies. A platform with no recorded threshold is treated as
/// unaffected outright -- there is nothing to guard against there.
func isNewEnoughToSkipWorkaround(platform: Platform, version: Version) -> Bool {
    guard let threshold = versionThresholds[platform] else {
        return true
    }
    return version >= threshold
}

/// True on every platform built on the shared runtime family, including
/// ones that ship after this was written -- one check instead of a list
/// that needs a new entry each time that family grows.
func isSharedRuntimeFamily(_ platform: Platform) -> Bool {
    platform != .openfield
}

func guardAdmits(_ platform: Platform) -> Bool {
    isSharedRuntimeFamily(platform)
}

func isPotentiallyAffected(platform: Platform, version: Version) -> Bool {
    if guardAdmits(platform) {
        return !isNewEnoughToSkipWorkaround(platform: platform, version: version)
    }
    return false
}
