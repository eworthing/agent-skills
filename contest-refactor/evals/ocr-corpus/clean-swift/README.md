# clean-swift restraint corpus

Ten small, hand-written Swift value types (plus one protocol/adapter pair and
one wiring file) covering every signal the `invariant` and `dead_surface`
detectors will implement:

- Two-sided **and** finite guards on `Double` parameters (`TrimSpan`, `FadeCurve`).
- A `min`/`max` clamp that rejects non-finite input before clamping (`GainLevel`).
- Uniqueness checks on `[UUID]` collections (`TrackSet`, `RosterList`).
- A `Codable` type with a custom `init(from:)` that delegates to a throwing
  initializer (`Snapshot`).
- An `Int(...)` conversion clamped to `Int`'s representable range before
  conversion (`DurationFormatter`).
- A protocol with requirements called from outside the conforming type
  (`PlaybackStatePort` / `LocalPlaybackAdapter`), and every declared case,
  requirement, and stored/computed property referenced somewhere in this
  folder (`Diagnostics.swift` is the wiring file that exercises the rest).

Shared by W1a (`invariant`) and W2 (`dead_surface`) restraint measurement:
this corpus must yield **zero** candidates from both detectors. A non-zero
result here is a detector bug, not a corpus finding -- neither detector may
emit `promotion_allowed: true`, and W0 makes no judgment claims about this
code; it exists only to be silent.
