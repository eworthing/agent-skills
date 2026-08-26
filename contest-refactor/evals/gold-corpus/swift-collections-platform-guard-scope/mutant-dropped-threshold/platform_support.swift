// Platform identity and a stdlib-bug workaround that only matters on a
// handful of platform families. The bug lives in a non-inlinable stdlib
// method whose precondition is bogus on old runtimes; once a platform's
// runtime is new enough, the bug is gone and no workaround is needed.

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
    .anchor: Version(major: 7, minor: 0),
    .companion: Version(major: 4, minor: 0),
    .parlor: Version(major: 9, minor: 0),
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

/// Every platform reaches the check below directly; nothing scopes which
/// platforms this applies to.
func guardAdmits(_ platform: Platform) -> Bool {
    true
}

func isPotentiallyAffected(platform: Platform, version: Version) -> Bool {
    !isNewEnoughToSkipWorkaround(platform: platform, version: version)
}
